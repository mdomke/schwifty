import pytest

from schwifty.checksum import algorithms
from schwifty.checksum.germany import Algorithm91
from schwifty.checksum.germany import digit_sum
from schwifty.checksum.germany import WeightedModulus
from schwifty.exceptions import InvalidAccountCode
from schwifty.exceptions import InvalidBBANChecksum


@pytest.mark.parametrize(
    ("account_code", "algorithm_name"),
    [
        # Method 02: remainder 0 reconciles to check digit 0.
        ("0000000000", "DE:02"),
        ("0009290701", "DE:00"),
        ("0539290858", "DE:00"),
        ("0001501824", "DE:00"),
        ("0001501832", "DE:00"),
        ("0094012341", "DE:06"),
        ("5073321010", "DE:06"),
        # Method 16 computes like method 06 over positions 1-9 (only method 15
        # is restricted to positions 6-9), so a valid method-06 account is valid
        # for method 16 too.
        ("0094012341", "DE:16"),
        # Remainder 1 is accepted when the last two digits match.
        ("0000000066", "DE:16"),
        ("0012345008", "DE:10"),
        ("0087654008", "DE:10"),
        ("1000000060", "DE:11"),
        # Remainder 1 would be check digit 10; method 11 maps that to 9.
        ("0000000069", "DE:11"),
        ("0446786040", "DE:17"),
        ("0240334000", "DE:19"),
        ("0200520016", "DE:19"),
        ("0000138301", "DE:24"),
        ("1306118605", "DE:24"),
        ("3307118608", "DE:24"),
        ("9307118603", "DE:24"),
        ("0521382181", "DE:25"),
        ("0520309001", "DE:26"),
        ("1111118111", "DE:26"),
        ("0005501024", "DE:26"),
        ("0009141405", "DE:32"),
        ("1709107983", "DE:32"),
        ("0122116979", "DE:32"),
        ("0121114867", "DE:32"),
        ("9030101192", "DE:32"),
        ("9245500460", "DE:32"),
        ("9913000700", "DE:34"),
        ("9914001000", "DE:34"),
        ("0000191919", "DE:38"),
        ("0001100660", "DE:38"),
        ("2063099200", "DE:61"),
        ("0260760481", "DE:61"),
        ("0123456600", "DE:63"),
        ("1234567893", "DE:21"),
        ("1234567895", "DE:22"),
        ("8889654328", "DE:68"),
        ("0987654324", "DE:68"),
        ("0987654328", "DE:68"),
        # Accounts in [400000000, 499999999] skip the check digit.
        ("0400000000", "DE:68"),
        ("0006543200", "DE:76"),
        ("9012345600", "DE:76"),
        ("7876543100", "DE:76"),
        ("0002525259", "DE:88"),
        ("0001000500", "DE:88"),
        ("0090013000", "DE:88"),
        ("0092525253", "DE:88"),
        ("0099913003", "DE:88"),
        ("2974118000", "DE:91"),
        ("5281741000", "DE:91"),
        ("9952810000", "DE:91"),
        ("2974117000", "DE:91"),
        ("5281770000", "DE:91"),
        ("9952812000", "DE:91"),
        ("8840019000", "DE:91"),
        ("8840050000", "DE:91"),
        ("8840087000", "DE:91"),
        ("8840045000", "DE:91"),
        ("8840012000", "DE:91"),
        ("8840055000", "DE:91"),
        ("8840080000", "DE:91"),
        ("0068007003", "DE:99"),
        ("0847321750", "DE:99"),
        ("0396000000", "DE:99"),
        ("0499999999", "DE:99"),
        # Method 99 accepts the whole range 0396000000 to 0499999999 without a check.
        ("0396000001", "DE:99"),
        ("0412345678", "DE:99"),
        # Method 08 applies no check digit below account number 60000, so an
        # account in [6000, 60000) is valid regardless of its check digit.
        ("0000006000", "DE:08"),
        ("0000059999", "DE:08"),
    ],
)
def test_german_checksum_success(account_code: str, algorithm_name: str) -> None:
    assert algorithms[algorithm_name].validate([account_code], "") is True


@pytest.mark.parametrize(
    ("account_code", "algorithm_name"),
    [
        ("8840017000", "DE:91"),
        ("8840023000", "DE:91"),
        ("8840041000", "DE:91"),
        ("8840014000", "DE:91"),
        ("8840026000", "DE:91"),
        ("8840011000", "DE:91"),
        ("8840025000", "DE:91"),
        ("8840062000", "DE:91"),
        ("8840010000", "DE:91"),
        ("8840057000", "DE:91"),
        # From account number 60000 upward method 08 does apply the check, so a
        # wrong check digit must still be rejected.
        ("0000060000", "DE:08"),
        # Method 02 with a non-zero, non-one remainder: the computed digit is 9.
        ("0000000010", "DE:02"),
        # Remainder 1 and a second digit outside {8, 9} is rejected.
        ("0000000060", "DE:25"),
        # Method 63 only accepts a leading zero.
        ("1123456600", "DE:63"),
        # Method 76 only accepts leading digits 0, 4, 6, 7, 8 and 9.
        ("1234567890", "DE:76"),
        # Just outside the exception range of method 99 the check digit applies again.
        ("0395999999", "DE:99"),
        ("0500000000", "DE:99"),
    ],
)
def test_german_checksum_failure(account_code: str, algorithm_name: str) -> None:
    assert algorithms[algorithm_name].validate([account_code], "") is False


def test_belgium_checksum() -> None:
    assert algorithms["BE:default"].validate(["539", "0075470"], "34") is True


def test_belgium_checksum_failure() -> None:
    assert algorithms["BE:default"].validate(["050", "0001234"], "56") is False


def test_belgium_checksum_checksum_edge_case() -> None:
    assert algorithms["BE:default"].validate(["050", "0000177"], "97") is True


def test_norway_checksum_checksum_edge_case() -> None:
    assert algorithms["NO:default"].validate(["6042", "143964"], "0") is True


def test_norway_checksum_invalid_check_digit() -> None:
    with pytest.raises(InvalidAccountCode, match="Invalid account code"):
        algorithms["NO:default"].validate(["6042", "100007"], "")


def test_german_checksum_68_solve() -> None:
    algo = algorithms["DE:68"]
    assert algo.solve(["1234567890"]) == ["1239567892"]
    assert algo.validate(["1239567892"], "") is True

    assert algo.solve(["0987654321"]) == ["0987654324"]
    assert algo.validate(["0987654324"], "") is True


def test_german_digit_sum_above_99() -> None:
    assert digit_sum(199) == 19


def test_german_checksum_02_invalid_remainder() -> None:
    with pytest.raises(InvalidBBANChecksum, match="Invalid remainder"):
        algorithms["DE:02"].validate(["0000000060"], "")


def test_german_checksum_08_skips_small_account() -> None:
    assert algorithms["DE:08"].compute(["0000001000"]) == ""


def test_german_checksum_09_has_no_check_digit() -> None:
    assert algorithms["DE:09"].compute(["0000000000"]) == ""


def test_german_checksum_63_solve_exhausted() -> None:
    # The check digit is not the leading position, so no candidate can satisfy
    # method 63 and the shared solver gives up.
    algo = algorithms["DE:63"]
    assert isinstance(algo, WeightedModulus)
    assert WeightedModulus.solve(algo, ["1123456789"]) is None


def test_german_checksum_91_compute_and_solve() -> None:
    algo = algorithms["DE:91"]
    assert algo.compute(["2974118000"]) == "8"
    assert algo.solve(["2974118000"]) == ["2974118000"]


def test_german_checksum_91_solve_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    # Each variant can always place a check digit, so the "none of them worked"
    # result is only reached when every variant declines.
    def no_solution(self: object, components: list[str]) -> None:
        return None

    for variant in (
        Algorithm91.Variant1,
        Algorithm91.Variant2,
        Algorithm91.Variant3,
        Algorithm91.Variant4,
    ):
        monkeypatch.setattr(variant, "solve", no_solution)

    assert algorithms["DE:91"].solve(["2974118000"]) is None
