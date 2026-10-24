"""Edge-case tests for :class:`schwifty.IBAN` beyond the happy path."""

from random import Random

import pytest

from schwifty import BBAN
from schwifty import exceptions
from schwifty import IBAN
from schwifty import registry


@pytest.mark.parametrize(
    ("canonical", "alias"),
    [
        # The ISO 7064 check digits are only ever generated in the range
        # 02..98, but the raw ``numeric % 97 == 1`` test also accepts the
        # aliases that differ by 97: 02/99, 98/01 and 97/00. Validation
        # compares against the canonically computed digits, so the aliases
        # must be rejected even though they pass the raw mod-97 test.
        ("DE02370400440000000024", "DE99370400440000000024"),
        ("DE98370400440000000042", "DE01370400440000000042"),
        ("DE97370400440000000060", "DE00370400440000000060"),
    ],
)
def test_checksum_digit_aliases_are_rejected(canonical: str, alias: str) -> None:
    assert IBAN(canonical).is_valid
    aliased = IBAN(alias, allow_invalid=True)
    assert aliased.numeric % 97 == 1
    assert aliased.is_valid is False
    with pytest.raises(exceptions.InvalidChecksumDigits):
        IBAN(alias)


@pytest.mark.parametrize(
    "raw",
    [
        "de89 3704 0044 0532 0130 00",
        "DE89\t3704004405320130 00",
        " de89 370400440532013000 ",
    ],
)
def test_constructor_normalises_input(raw: str) -> None:
    # Whitespace (including tabs and padding) is stripped and the value is
    # upper-cased before validation.
    assert IBAN(raw).compact == "DE89370400440532013000"


def test_iban_properties_fr() -> None:
    iban = IBAN("FR1420041010050500013M02606")
    assert iban.bank_code == "20041"
    assert iban.branch_code == "01005"
    assert iban.account_code == "0500013M026"
    assert iban.national_checksum_digits == "06"
    assert iban.in_sepa_zone is True


def test_iban_properties_es() -> None:
    iban = IBAN("ES9121000418450200051332")
    assert iban.bank_code == "2100"
    assert iban.branch_code == "0418"
    assert iban.account_code == "0200051332"
    assert iban.national_checksum_digits == "45"


def test_iban_properties_gb() -> None:
    iban = IBAN("GB29NWBK60161331926819")
    assert iban.bank_code == "NWBK"
    # The British branch code is the sort code.
    assert iban.branch_code == "601613"
    assert iban.account_code == "31926819"
    assert iban.national_checksum_digits == ""


def test_iban_properties_nl() -> None:
    iban = IBAN("NL91ABNA0417164300")
    assert iban.bank_code == "ABNA"
    assert iban.branch_code == ""
    assert iban.account_code == "0417164300"


def test_iban_properties_be() -> None:
    iban = IBAN("BE68539007547034")
    assert iban.bank_code == "539"
    assert iban.account_code == "0075470"
    assert iban.national_checksum_digits == "34"


def test_iban_properties_no() -> None:
    iban = IBAN("NO9386011117947")
    assert iban.bank_code == "8601"
    assert iban.account_code == "111794"
    assert iban.national_checksum_digits == "7"
    # The trailing block of the formatted form has only three characters.
    assert iban.formatted == "NO93 8601 1117 947"


def test_iban_exotic_components() -> None:
    # Seychelles: the currency code is part of the BBAN.
    assert IBAN("SC18SSCB11010000000000001497USD").currency_code == "USD"
    # Brazil: account id and account type.
    brazil = IBAN("BR9700360305000010009795493P1")
    assert brazil.account_id == "1"
    assert brazil.account_type == "P"
    # Guatemala: account type and currency code.
    guatemala = IBAN("GT82TRAJ01020000001210029690")
    assert guatemala.account_type == "02"
    assert guatemala.currency_code == "01"


def test_iban_country_can_be_unknown_to_pycountry() -> None:
    # Kosovo has an IBAN specification but no pycountry entry.
    iban = IBAN("XK051212012345678906")
    assert iban.country is None
    assert iban.in_sepa_zone is False


def test_iban_numeric_mod97() -> None:
    for code in ("DE89370400440532013000", "FR1420041010050500013M02606"):
        assert IBAN(code).numeric % 97 == 1


def test_invalid_national_checksum_is_reported_on_request() -> None:
    # Take the valid Italian IBAN and corrupt its national check character
    # (the CIN). Recomputing the IBAN check digits keeps the IBAN itself
    # valid, so only the explicit BBAN validation can notice.
    bban = IBAN("IT60X0542811101000000123456").bban
    doctored = IBAN.from_bban("IT", "A" + str(bban)[1:])
    assert doctored.is_valid
    with pytest.raises(exceptions.InvalidBBANChecksum):
        doctored.validate(validate_bban=True)
    with pytest.raises(exceptions.InvalidBBANChecksum):
        IBAN(doctored.compact, validate_bban=True)


def test_from_bban_accepts_bban_objects() -> None:
    bban = BBAN("DE", "370400440532013000")
    iban = IBAN.from_bban("DE", bban)
    assert isinstance(iban, IBAN)
    assert iban.compact == "DE89370400440532013000"


def test_random_with_seed_is_reproducible() -> None:
    first = IBAN.random(country_code="DE", random=Random(7))  # noqa: S311
    second = IBAN.random(country_code="DE", random=Random(7))  # noqa: S311
    assert first == second
    other = IBAN.random(country_code="DE", random=Random(8))  # noqa: S311
    assert first != other


def test_random_without_registry() -> None:
    iban = IBAN.random(country_code="FR", random=Random(3), use_registry=False)  # noqa: S311
    assert iban.country_code == "FR"
    assert iban.is_valid
    assert iban.validate(validate_bban=True) is True


def test_random_any_country() -> None:
    iban = IBAN.random(random=Random(11))  # noqa: S311
    assert iban.is_valid
    assert iban.country_code == iban.bban.country_code


def test_is_aspirational() -> None:
    assert IBAN("SN08SN0100152000048500003035").is_aspirational is True
    assert IBAN("DE89370400440532013000").is_aspirational is False
    assert BBAN("SN", "SN0100152000048500003035").is_aspirational is True
    assert BBAN("DE", "370400440532013000").is_aspirational is False


def test_aspirational_countries_are_not_in_official_registry() -> None:
    # Once a country is added to the official SWIFT registry, its ``aspirational`` flag must be
    # removed from ``overwrite.json``.
    import json
    from pathlib import Path

    import schwifty

    official = json.loads(
        (Path(schwifty.__file__).parent / "iban_registry" / "generated.json").read_text()
    )
    assert not any(registry.get_iban_spec(country).aspirational for country in official)
