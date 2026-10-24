"""Direct tests for the national checksum algorithms outside Germany.

The existing suite covers the German methods as well as the Belgian and
Norwegian defaults in depth. This module covers the remaining registered
algorithms (FR/MC, ES, IT/SM, CZ/SK, EE, FI, IS, PL and the ISO 7064
mod-97-10 group) plus the shared helpers in :mod:`schwifty.checksum`.
"""

import pytest

from schwifty.checksum import algorithms
from schwifty.checksum import iso7064
from schwifty.checksum import luhn
from schwifty.checksum import numerify
from schwifty.checksum import weighted
from schwifty.checksum.netherlands import DefaultAlgorithm as DutchAlgorithm
from schwifty.domain import Component


def test_numerify() -> None:
    assert numerify("0") == 0
    assert numerify("9") == 9
    # Letters map to their position in the digit+uppercase alphabet (A -> 10).
    assert numerify("A") == 10
    assert numerify("Z9") == 359
    assert numerify("DE89") == 131489


def test_weighted() -> None:
    assert weighted("123", 10, [1, 2, 3]) == 4
    # ``zip`` stops at the shorter input, so surplus digits are ignored.
    assert weighted("12345", 10, [1, 1]) == 3


def test_luhn() -> None:
    assert luhn("7992739871") == "3"
    assert luhn("12345600007") == "4"


def test_iso7064_helper() -> None:
    assert iso7064(12345, 97, lambda r: 98 - r) == "72"
    assert iso7064(100, 11, lambda r: r, n_digits=1) == "1"


def test_registered_non_german_algorithms() -> None:
    expected = {
        "BA",
        "BE",
        "CZ",
        "EE",
        "ES",
        "FI",
        "FR",
        "IS",
        "IT",
        "MC",
        "ME",
        "MK",
        "MR",
        "NO",
        "PL",
        "PT",
        "RS",
        "SI",
        "SK",
        "SM",
        "TL",
        "TN",
    }
    registered = {key.split(":")[0] for key in algorithms if not key.startswith("DE")}
    assert registered == expected
    # Germany only registers named methods, and the Dutch algorithm is
    # deliberately not registered anymore.
    assert "DE:default" not in algorithms
    assert "NL:default" not in algorithms


def test_france_checksum() -> None:
    algo = algorithms["FR:default"]
    components = ["20041", "01005", "0500013M026"]
    assert algo.compute(components) == "06"
    assert algo.validate(components, "06") is True
    assert algo.validate(components, "07") is False


def test_monaco_uses_the_french_checksum() -> None:
    components = ["20041", "01005", "0500013M026"]
    assert algorithms["MC:default"].compute(components) == "06"


def test_spain_checksum() -> None:
    algo = algorithms["ES:default"]
    components = ["2100", "0418", "0200051332"]
    assert algo.compute(components) == "45"
    assert algo.validate(components, "45") is True
    assert algo.validate(components, "46") is False


def test_spain_checksum_reconciles_edge_values() -> None:
    # A weighted remainder of 0 yields 11 - 0 = 11, which the Spanish
    # algorithm reconciles to the check digit 0.
    assert algorithms["ES:default"].compute(["0000", "0000", "0000000000"]) == "00"


def test_italy_checksum() -> None:
    algo = algorithms["IT:default"]
    components = ["05428", "11101", "000000123456"]
    assert algo.compute(components) == "X"
    assert algo.validate(components, "X") is True
    assert algo.validate(components, "A") is False


def test_san_marino_uses_the_italian_checksum() -> None:
    components = ["03225", "09800", "000000270100"]
    assert algorithms["SM:default"].compute(components) == "U"


def test_czech_checksum() -> None:
    algo = algorithms["CZ:default"]
    assert algo.accepts == [Component.BRANCH_CODE, Component.ACCOUNT_CODE]
    # The Czech algorithm has no dedicated check digit: validity means both
    # the branch and the account code weigh to 0 modulo 11.
    assert algo.compute(["000019", "2000145399"]) == ""
    assert algo.validate(["000019", "2000145399"], "") is True
    assert algo.validate(["000019", "2000145390"], "") is False


def test_czech_checksum_solve_repairs_the_trailing_digit() -> None:
    algo = algorithms["CZ:default"]
    assert algo.solve(["000019", "2000145390"]) == ["000019", "2000145399"]
    assert algo.solve(["000019", "2000145399"]) == ["000019", "2000145399"]


def test_slovakia_uses_the_czech_checksum() -> None:
    assert algorithms["SK:default"].validate(["000019", "8742637541"], "") is True


def test_estonia_checksum() -> None:
    algo = algorithms["EE:default"]
    components = ["00", "22102014568"]
    assert algo.compute(components) == "5"
    assert algo.validate(components, "5") is True
    assert algo.validate(components, "6") is False


def test_finland_checksum() -> None:
    algo = algorithms["FI:default"]
    components = ["123", "4560000078"]
    assert algo.compute(components) == "5"
    assert algo.validate(components, "5") is True
    assert algo.validate(components, "6") is False


def test_iceland_checksum() -> None:
    algo = algorithms["IS:default"]
    assert algo.accepts == [Component.ACCOUNT_HOLDER_ID]
    # The check digit lives inside the account holder id at index 8.
    assert algo.compute(["5510730339"]) == "3"
    assert algo.validate(["5510730339"], "") is True
    assert algo.validate(["5510730349"], "") is False


def test_iceland_checksum_solve() -> None:
    algo = algorithms["IS:default"]
    assert algo.solve(["5510730309"]) == ["5510730339"]


def test_iceland_checksum_unsolvable_holder_id() -> None:
    # This holder id would require the check digit 10, which no single
    # digit can supply, so it can never validate and cannot be solved.
    algo = algorithms["IS:default"]
    assert algo.compute(["0000000600"]) == "10"
    assert algo.validate(["0000000600"], "") is False
    assert algo.solve(["0000000600"]) is None


def test_poland_checksum() -> None:
    algo = algorithms["PL:default"]
    assert algo.accepts == [Component.BANK_CODE, Component.BRANCH_CODE]
    assert algo.compute(["109", "0101"]) == "4"
    assert algo.compute(["114", "0101"]) == "0"
    assert algo.validate(["109", "0101"], "4") is True
    assert algo.validate(["109", "0101"], "5") is False


@pytest.mark.parametrize("country_code", ["BA", "ME", "MK", "PT", "RS", "SI", "TL"])
def test_iso7064_group_checksum(country_code: str) -> None:
    # These countries share the plain ISO 7064 mod-97-10 algorithm, fed with
    # the Portuguese example BBAN (without its check digits).
    algo = algorithms[f"{country_code}:default"]
    assert algo.compute(["0002012312345678901"]) == "54"
    assert algo.validate(["0002012312345678901"], "54") is True
    assert algo.validate(["0002012312345678901"], "55") is False


def test_bosnia_checksum() -> None:
    assert algorithms["BA:default"].compute(["12900794010284"]) == "94"


def test_mauritania_and_tunisia_variant_checksum() -> None:
    # MR and TN use the 97 - r post-processing variant of ISO 7064.
    assert algorithms["MR:default"].compute(["00020", "00101", "00001234567"]) == "53"
    assert algorithms["TN:default"].compute(["10", "006", "0351835984788"]) == "31"


def test_dutch_checksum_is_available_but_unregistered() -> None:
    # The Dutch eleven-test is kept in the codebase but no longer registered,
    # because it is not used for Dutch IBANs anymore.
    algo = DutchAlgorithm()
    assert algo.compute(["0417164300"]) == ""
    assert algo.validate(["0417164300"], "") is True
    assert algo.validate(["0417164301"], "") is False


def test_base_algorithm_solve_returns_components_unchanged() -> None:
    # Algorithms whose checksum occupies its own BBAN field have nothing to
    # adjust; the inherited ``solve`` is a pass-through.
    components = ["2100", "0418", "0200051332"]
    assert algorithms["ES:default"].solve(components) == components
    assert algorithms["FR:default"].solve(["20041", "01005", "0500013M026"]) == [
        "20041",
        "01005",
        "0500013M026",
    ]
