import copy
import pickle
from random import Random

import pytest

from schwifty import IBAN
from schwifty import registry
from schwifty.bban import BBAN
from schwifty.exceptions import GenerateRandomOverflowError
from schwifty.exceptions import InvalidAccountCode
from schwifty.exceptions import InvalidBBANChecksum
from schwifty.exceptions import SchwiftyException


def test_validate_national_checksum() -> None:
    # A valid national checksum returns True (consistent with the "no checksum
    # algorithm" case), while an invalid one raises InvalidBBANChecksum.
    assert BBAN("BE", "539007547034").validate_national_checksum() is True
    assert BBAN("GB", "WEST12345698765432").validate_national_checksum() is True
    with pytest.raises(InvalidBBANChecksum):
        BBAN("BE", "539007547035").validate_national_checksum()

    # Bosnia and Herzegovina (BA) uses ISO 7064 mod 97-10; it was previously
    # registered under the wrong country code "BT" (#264), so the national
    # checksum was never validated.
    assert BBAN("BA", "1290079401028494").validate_national_checksum() is True
    with pytest.raises(InvalidBBANChecksum):
        BBAN("BA", "1290079401028400").validate_national_checksum()


def test_validate_german_national_checksum() -> None:
    # The per-bank German checksum method is selected via the bank's
    # ``checksum_algo`` field. Commerzbank (bank code 37040044) uses method 13,
    # whose check digit sits at account position 8. A matching account validates;
    # a corrupted check digit raises. This path was silently skipped while
    # ``checksum_algo`` was dropped during registry deserialization.
    assert BBAN("DE", "370400440532013000").validate_national_checksum() is True
    with pytest.raises(InvalidBBANChecksum):
        BBAN("DE", "370400440532013100").validate_national_checksum()


def test_bank_prefers_the_primary_registry_record() -> None:
    # A national registry lists one record per branch, so a bank code maps to
    # several entries and ``primary`` marks the institution's main record.
    # ``BBAN.bank`` returned the first match in file order instead, which made
    # ``IBAN.bank``/``IBAN.bank_name`` describe a different institution than
    # ``IBAN.bic`` does: for the Nord LB codes the branch record is listed before
    # the institution's own record.
    iban = IBAN.generate("DE", "29050000", "0000000000")
    assert iban.bic == "BRLADE22XXX"
    assert iban.bank is not None
    assert iban.bank.bic == iban.bic
    assert iban.bank.primary is True
    assert iban.bank_short_name == "Nord LB Bremen"


def test_bank_prefers_the_primary_record_of_every_registered_bank_code() -> None:
    # Whenever the registry marks a record of a bank code as the primary one, that
    # is the record the bank code has to resolve to. ``BBAN.bank`` used to return
    # whichever entry happened to be read first.
    not_primary = []
    for country_code in registry.get_countries():
        for bank_code in sorted(
            {bank.bank_code for bank in registry.get_banks_by_country(country_code)}
        ):
            entries = registry.get_banks_by_code(country_code, bank_code)
            if not bank_code or not any(bank.primary for bank in entries):
                continue
            bban = BBAN.from_components(country_code, bank_code=bank_code)
            if bban.bank is not None and not bban.bank.primary:
                not_primary.append((country_code, bank_code, bban.bank.bic))
    assert not not_primary


def test_validate_national_checksum_on_truncated_bban() -> None:
    with pytest.raises(InvalidAccountCode):
        BBAN("DE", "3704004405320").validate_national_checksum()


def test_dict_access_is_deprecated() -> None:
    # ``IBAN.bank`` / ``IBAN.spec`` (and their BBAN counterparts) used to return
    # dicts; subscription and ``.get()`` are kept working for backward
    # compatibility but now emit a DeprecationWarning in favour of attribute
    # access.
    bban = BBAN("DE", "370400440532013000")
    bank = bban.bank
    assert bank is not None
    with pytest.deprecated_call():
        assert bank["name"] == bank.name
    with pytest.deprecated_call():
        assert bank.get("checksum_algo") == bank.checksum_algo
    with pytest.deprecated_call():
        assert bban.spec["bban_length"] == bban.spec.bban_length


@pytest.mark.parametrize("country_code", ["DE", "ES", "GB", "FR", "PL"])
def test_random(country_code: str) -> None:
    n = 100
    bbans = {BBAN.random(country_code) for _ in range(n)}
    assert len(bbans) == n

    for bban in bbans:
        assert bban.bank is not None
        assert bban.country_code == country_code

    assert any(
        bban.bank is None
        for bban in (BBAN.random(country_code, use_registry=False) for _ in range(n))
    )


def test_random_national_checksum_overflow(monkeypatch: pytest.MonkeyPatch) -> None:
    # When no generated candidate ever satisfies the national checksum, random()
    # exhausts its retries and raises GenerateRandomOverflowError rather than
    # returning a BBAN with an invalid checksum.
    def always_invalid(self: BBAN) -> bool:
        raise InvalidBBANChecksum

    monkeypatch.setattr(BBAN, "validate_national_checksum", always_invalid)
    with pytest.raises(GenerateRandomOverflowError):
        BBAN.random("DE")


def test_pickle_roundtrip() -> None:
    bban = BBAN("CH", "04835012345678009")
    for proto in range(pickle.HIGHEST_PROTOCOL + 1):
        restored = pickle.loads(pickle.dumps(bban, protocol=proto))
        assert restored == bban
        assert restored.country_code == bban.country_code


def test_deepcopy() -> None:
    bban = BBAN("CH", "04835012345678009")
    bban_copy = copy.deepcopy(bban)
    assert bban_copy == bban
    assert bban_copy.country_code == bban.country_code
    assert id(bban_copy) != id(bban)


@pytest.mark.parametrize("country_code", ["AO", "GW", "IR", "KM", "MG", "MZ"])
def test_random_countries_without_positions(country_code: str) -> None:
    # These registry entries define a BBAN regex but no component positions.
    # random() must fall back to generating from the regex instead of
    # degenerating to an all-zero BBAN through from_components().
    iban = IBAN.random(country_code=country_code, random=Random(42), use_registry=False)  # noqa: S311
    assert iban.is_valid
    assert str(iban.bban) != "0" * len(iban.bban)


def test_random_honduras() -> None:
    # The Honduran BBAN spec (4!a20!n) has no component positions either, but
    # unlike the all-digit specs above an all-zero BBAN can never satisfy the
    # '4!a' part, so IBAN.random("HN") used to raise InvalidStructure.
    iban = IBAN.random(country_code="HN", random=Random(42), use_registry=False)  # noqa: S311
    assert iban.is_valid
    assert str(iban.bban) != "0" * len(iban.bban)


def test_from_components_unsupported_country() -> None:
    # Without component positions a BBAN cannot be assembled from components.
    # This raises the explicit "not supported" error rather than the misleading
    # "Bank code exceeds maximum size 0".
    with pytest.raises(SchwiftyException, match="BBAN generation for HN not supported"):
        BBAN.from_components("HN", bank_code="BGAH", account_code="12345678901234567890")
