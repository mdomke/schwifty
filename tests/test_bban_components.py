"""Tests for BBAN assembly from components and component access."""

from random import Random

import pytest

from schwifty import exceptions
from schwifty import IBAN
from schwifty.bban import BBAN
from schwifty.bban import compute_national_checksum
from schwifty.domain import Component


def test_from_components_pads_components_with_zeros() -> None:
    bban = BBAN.from_components("DE", bank_code="37040044", account_code="532013000")
    assert str(bban) == "370400440532013000"
    assert bban.account_code == "0532013000"


def test_from_components_splits_combined_bank_and_branch_code() -> None:
    # If the bank code is given together with the branch code (sort code),
    # the overlapping part is split into the branch code.
    bban = BBAN.from_components("GB", bank_code="NWBK601613", account_code="31926819")
    assert str(bban) == "NWBK60161331926819"
    assert bban.bank_code == "NWBK"
    assert bban.branch_code == "601613"


def test_from_components_computes_national_checksum() -> None:
    bban = BBAN.from_components(
        "IT", bank_code="05428", branch_code="11101", account_code="000000123456"
    )
    assert str(bban) == "X0542811101000000123456"
    assert bban.national_checksum_digits == "X"

    bban = BBAN.from_components("BE", bank_code="539", account_code="0075470")
    assert str(bban) == "539007547034"
    assert bban.national_checksum_digits == "34"


def test_from_components_bank_code_too_long() -> None:
    with pytest.raises(exceptions.InvalidBankCode, match="Bank code exceeds maximum size 8"):
        BBAN.from_components("DE", bank_code="123456789", account_code="1")


def test_from_components_branch_code_too_long() -> None:
    with pytest.raises(exceptions.InvalidBranchCode, match="Branch code exceeds maximum size 5"):
        BBAN.from_components("IT", bank_code="12345", branch_code="123456", account_code="1")


def test_from_components_account_code_too_long() -> None:
    with pytest.raises(exceptions.InvalidAccountCode, match="Account code exceeds maximum size 10"):
        BBAN.from_components("DE", bank_code="12345678", account_code="12345678901")


def test_from_components_unknown_country() -> None:
    with pytest.raises(exceptions.InvalidCountryCode, match="Unknown country-code 'XX'"):
        BBAN.from_components("XX", bank_code="1", account_code="1")


def test_generate_with_too_long_bank_code() -> None:
    with pytest.raises(exceptions.InvalidBankCode):
        IBAN.generate("DE", "012345678", "7000123456")


def test_compute_national_checksum_without_algorithm() -> None:
    # Countries without a registered default algorithm (and Germany, which
    # only registers named per-bank methods) yield an empty checksum.
    components = {
        Component.BANK_CODE: "NWBK",
        Component.BRANCH_CODE: "601613",
        Component.ACCOUNT_CODE: "31926819",
    }
    assert compute_national_checksum("GB", components) == ""
    assert compute_national_checksum("DE", components) == ""


def test_compute_national_checksum_belgium() -> None:
    components = {
        Component.BANK_CODE: "539",
        Component.BRANCH_CODE: "",
        Component.ACCOUNT_CODE: "0075470",
    }
    assert compute_national_checksum("BE", components) == "34"


def test_bban_exotic_components() -> None:
    bban = IBAN("BR9700360305000010009795493P1").bban
    assert bban.account_id == "1"
    assert bban.account_type == "P"
    assert IBAN("SC18SSCB11010000000000001497USD").bban.currency_code == "USD"
    holder = IBAN("IS140159260076545510730339").bban
    assert holder.account_holder_id == "5510730339"


def test_bban_random_with_seed_is_reproducible() -> None:
    first = BBAN.random("ES", random=Random(5))  # noqa: S311
    second = BBAN.random("ES", random=Random(5))  # noqa: S311
    assert first == second
    assert first.country_code == "ES"
    assert first.validate_national_checksum() is True
