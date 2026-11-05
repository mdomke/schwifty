"""Tests for the status of bank codes and how it affects lookups (see ADR 3)."""

import pytest

from schwifty import BBAN
from schwifty import BIC
from schwifty import registry
from schwifty.domain import Bank
from schwifty.domain import BankStatus
from schwifty.domain import lookup_rank
from schwifty.registry import Registry


def bank(bic: str, status: BankStatus = BankStatus.ACTIVE, *, primary: bool) -> Bank:
    return Bank("DE", bic, "10000000", f"Bank {bic}", primary=primary, status=status)


@pytest.fixture
def records(monkeypatch: pytest.MonkeyPatch) -> list[Bank]:
    entries: list[Bank] = []
    monkeypatch.setattr(registry, "get_banks_by_code", lambda *_: entries)
    return entries


def test_parse_bank_reads_status_fields() -> None:
    parsed = Registry()._parse_bank(
        {
            "country_code": "SI",
            "bic": "KBMASI2XXXX",
            "bank_code": "06000",
            "name": "OTP BANKA D.D.",
            "status": "merged",
            "successor_bank_code": "04000",
            "legacy_name": "NOVA KBM D.D.",
        }
    )
    assert parsed.status is BankStatus.MERGED
    assert parsed.successor_bank_code == "04000"
    assert parsed.legacy_name == "NOVA KBM D.D."


def test_parse_bank_defaults_to_active() -> None:
    parsed = Registry()._parse_bank(
        {"country_code": "DE", "bic": "TESTDEFF", "bank_code": "10000000", "name": "Test"}
    )
    assert parsed.status is BankStatus.ACTIVE
    assert parsed.successor_bank_code is None
    assert parsed.legacy_name is None


def test_parse_bank_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="retired"):
        Registry()._parse_bank(
            {
                "country_code": "DE",
                "bic": "TESTDEFF",
                "bank_code": "10000000",
                "name": "Test",
                "status": "retired",
            }
        )


def test_lookup_rank_orders_by_status_before_primary() -> None:
    ranked = sorted(
        [
            bank("DLSTDEFF", BankStatus.DELISTED, primary=True),
            bank("CLSDDEFF", BankStatus.CLOSED, primary=False),
            bank("BRCHDEFF", primary=False),
            bank("MRGDDEFF", BankStatus.MERGED, primary=False),
            bank("HEADDEFF", primary=True),
        ],
        key=lookup_rank,
        reverse=True,
    )
    assert [entry.bic for entry in ranked] == [
        "HEADDEFF",  # active and primary
        "BRCHDEFF",  # active branch, preferred over any retired record
        "MRGDDEFF",  # merged, since the code still leads to a successor
        "DLSTDEFF",  # closed and delisted rank equally, so primary decides
        "CLSDDEFF",
    ]


def test_bank_prefers_active_branch_over_retired_head_office(records: list[Bank]) -> None:
    records.extend(
        [
            bank("HEADDEFF", BankStatus.DELISTED, primary=True),
            bank("BRCHDEFF", primary=False),
        ]
    )
    resolved = BBAN.from_components("DE", bank_code="10000000").bank
    assert resolved is not None
    assert resolved.bic == "BRCHDEFF"


def test_bank_prefers_primary_among_active_records(records: list[Bank]) -> None:
    records.extend([bank("BRCHDEFF", primary=False), bank("HEADDEFF", primary=True)])
    resolved = BBAN.from_components("DE", bank_code="10000000").bank
    assert resolved is not None
    assert resolved.bic == "HEADDEFF"


def test_bank_prefers_merged_over_delisted(records: list[Bank]) -> None:
    records.extend(
        [
            bank("DLSTDEFF", BankStatus.DELISTED, primary=True),
            bank("MRGDDEFF", BankStatus.MERGED, primary=False),
        ]
    )
    resolved = BBAN.from_components("DE", bank_code="10000000").bank
    assert resolved is not None
    assert resolved.status is BankStatus.MERGED


def test_bic_candidates_are_ordered_by_rank(records: list[Bank]) -> None:
    records.extend(
        [
            bank("DLSTDEFF", BankStatus.DELISTED, primary=True),
            bank("MRGDDEFF", BankStatus.MERGED, primary=True),
            bank("BRCHDEFF", primary=False),
        ]
    )
    candidates = BIC.candidates_from_bank_code("DE", "10000000")
    assert [candidate.compact for candidate in candidates] == ["BRCHDEFF", "MRGDDEFF", "DLSTDEFF"]


def test_bic_from_bank_code_prefers_active_over_retired_primary(records: list[Bank]) -> None:
    # Both codes are equally generic, so only the rank of their records decides. The retired
    # head office would win the alphabetical tie-break.
    records.extend(
        [
            bank("ZZZZDEFF", BankStatus.DELISTED, primary=True),
            bank("AAAADEFF", primary=False),
        ]
    )
    assert BIC.from_bank_code("DE", "10000000") == "AAAADEFF"
