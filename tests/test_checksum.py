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
        # Method 31 test account numbers. Positions 1 to 9 are weighted 1 to 9 from left to
        # right and the remainder of the sum divided by 11 is the check digit at position 10.
        ("1000000524", "DE:31"),
        ("1000000583", "DE:31"),
        # The example from the document: 0*1 + 2*2 + 6*3 + 3*4 + 1*5 + 6*6 + 0*7 + 1*8 + 6*9
        # = 137, 137 % 11 = 5.
        ("0263160165", "DE:31"),
        # Remainder 1 is check digit 1, nothing is subtracted from 11 like in method 06.
        ("1000000001", "DE:31"),
        # 1*2 + 1*9 = 11, remainder 0 gives check digit 0.
        ("0100000010", "DE:31"),
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
        # Method 40 test account numbers. Positions 1 to 9 are weighted 6, 3, 7, 9, 10, 5, 8,
        # 4, 2 and the check digit is at position 10.
        ("0001258345", "DE:40"),
        ("0003231963", "DE:40"),
        # 1*6 + 2*3 + 3*7 + 4*9 + 5*10 + 6*5 + 7*8 + 8*4 + 9*2 = 255, 255 % 11 = 2, 11 - 2 = 9.
        ("1234567899", "DE:40"),
        # Method 41 test account numbers. They are computed like method 00.
        ("4013410024", "DE:41"),
        ("4016660195", "DE:41"),
        ("0166805317", "DE:41"),
        ("4019310079", "DE:41"),
        ("4019340829", "DE:41"),
        ("4019151002", "DE:41"),
        # If position 4 is a 9, positions 1 to 3 are not part of the calculation. This is
        # the example from the document: 9*1 + 1*2 + 1*1 = 12, 10 - 2 = 8.
        ("4019110008", "DE:41"),
        # Method 00 would expect check digit 1 here.
        ("9999110008", "DE:41"),
        # Method 42 test account numbers. Positions 2 to 9 are weighted 9, 8, 7, 6, 5, 4, 3,
        # 2 and the check digit is at position 10.
        ("0000059498", "DE:42"),
        # 1*2 + 5*3 + 9*4 + 5*5 = 78, remainder 1 gives check digit 0 as in method 06.
        ("0000059510", "DE:42"),
        # 2*9 + 3*8 + 4*7 + 5*6 + 6*5 + 7*4 + 8*3 + 9*2 = 200, 200 % 11 = 2, 11 - 2 = 9.
        ("1234567899", "DE:42"),
        # Position 1 is not part of the calculation.
        ("9000059498", "DE:42"),
        # Method 43 test account numbers. Positions 1 to 9 are weighted 9, 8, 7, 6, 5, 4, 3,
        # 2, 1 and the check digit is 10 minus the remainder of the sum divided by 10.
        ("0006135244", "DE:43"),
        ("9516893476", "DE:43"),
        # 9*9 + 5*8 + 1*7 + 6*6 + 8*5 + 9*4 + 3*3 + 4*2 + 3*1 = 260, a difference of 10 gives
        # check digit 0.
        ("9516893430", "DE:43"),
        # Method 44 test account numbers. Only positions 5 to 9 are weighted, with 10, 5, 8,
        # 4, 2, and the check digit is at position 10.
        ("0000889006", "DE:44"),
        ("2618040504", "DE:44"),
        # Positions 1 to 4 are not part of the calculation.
        ("9999889006", "DE:44"),
        # The Bundesbank document has no test account numbers for method 48. Positions
        # 3 to 8 are weighted 7, 6, 5, 4, 3, 2 and the check digit is at position 9:
        # 3*7 + 4*6 + 5*5 + 6*4 + 7*3 + 8*2 = 131, 131 % 11 = 10, 11 - 10 = 1.
        ("1234567810", "DE:48"),
        # Positions 1, 2 and 10 are not part of the calculation.
        ("9934567817", "DE:48"),
        # 2*5 + 5*4 + 4*3 + 1*2 = 44, remainder 0 gives check digit 0.
        ("0000254100", "DE:48"),
        # 9*7 + 9*6 + 9*5 + 9*4 + 9*3 + 9*2 = 243, remainder 1 gives check digit 0 too.
        ("0099999900", "DE:48"),
        # Method 46 test account numbers. Only positions 3 to 7 are weighted and the check
        # digit is at position 8.
        ("0235468612", "DE:46"),
        ("0837890901", "DE:46"),
        ("1041447600", "DE:46"),
        # Positions 1, 2, 9 and 10 are not part of the calculation.
        ("9935468699", "DE:46"),
        # Method 47 test account numbers. Only positions 4 to 8 are weighted and the check
        # digit is at position 9.
        ("0001018000", "DE:47"),
        ("1003554450", "DE:47"),
        # Positions 1 to 3 and 10 are not part of the calculation.
        ("9993554459", "DE:47"),
        # The Bundesbank document has no test account numbers for method 49. It checks with
        # method 00 first, so the method 00 test account numbers are valid, also those that
        # method 01 rejects.
        ("0009290701", "DE:49"),
        ("0539290858", "DE:49"),
        ("0001501824", "DE:49"),
        # Method 00 expects check digit 7 here, but method 01 accepts it:
        # 9*3 + 8*7 + 7*1 + 6*3 + 5*7 + 4*1 + 3*3 + 2*7 + 1*1 = 171, 10 - 1 = 9.
        ("1234567899", "DE:49"),
        # Method 50 test account numbers. The sub-account at positions 8 to 10 is not part
        # of the calculation.
        ("4000005001", "DE:50"),
        ("4444442001", "DE:50"),
        ("4000005999", "DE:50"),
        # Without the sub-account "000" the account code is shifted three positions left.
        ("0004000005", "DE:50"),
        ("0004444442", "DE:50"),
        ("2063099200", "DE:61"),
        ("0260760481", "DE:61"),
        ("0123456600", "DE:63"),
        # The sub-account "00" may be omitted, moving the check digit to position 10.
        ("0001234566", "DE:63"),
        ("0000123456", "DE:76"),
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
        ("0068007003", "DE:95"),
        ("0847321750", "DE:95"),
        ("6450060494", "DE:95"),
        ("6454000003", "DE:95"),
        # Method 95 has no check digit for these account ranges.
        ("0000000001", "DE:95"),
        ("0001999999", "DE:95"),
        ("0009000000", "DE:95"),
        ("0025999999", "DE:95"),
        ("0396000000", "DE:95"),
        ("0499999999", "DE:95"),
        ("0700000000", "DE:95"),
        ("0799999999", "DE:95"),
        ("0910000000", "DE:95"),
        ("0989999999", "DE:95"),
        ("0068007003", "DE:99"),
        ("0847321750", "DE:99"),
        ("0396000000", "DE:99"),
        ("0499999999", "DE:99"),
        ("3456789019", "DE:A2"),
        ("5678901231", "DE:A2"),
        ("6789012348", "DE:A2"),
        ("3456789012", "DE:A2"),
        ("1234567897", "DE:A3"),
        ("0123456782", "DE:A3"),
        ("9876543210", "DE:A3"),
        ("1234567890", "DE:A3"),
        ("0123456789", "DE:A3"),
        # Method C1, variant 1 (method 17) for account codes not starting with 5.
        ("0446786040", "DE:C1"),
        ("0478046940", "DE:C1"),
        ("0701625830", "DE:C1"),
        ("0701625840", "DE:C1"),
        ("0882095630", "DE:C1"),
        # Method C1, variant 2 for account codes starting with 5.
        ("5432112349", "DE:C1"),
        ("5543223456", "DE:C1"),
        ("5654334563", "DE:C1"),
        ("5765445670", "DE:C1"),
        ("5876556788", "DE:C1"),
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
        # Without the sub-account the check digit at position 10 still has to match.
        ("0001234567", "DE:63"),
        # Method 48 with a wrong check digit at position 9.
        ("1234567890", "DE:48"),
        ("0099999910", "DE:48"),
        # Valid for method 06, but method 48 expects check digit 7 at position 9.
        ("0094012341", "DE:48"),
        # Method 31 with a wrong check digit.
        ("1000000525", "DE:31"),
        # Method 40 with a wrong check digit.
        ("0001258346", "DE:40"),
        # Method 41 with a wrong check digit.
        ("4013410025", "DE:41"),
        # Valid for method 00, but position 4 is a 9, so method 41 expects check digit 8.
        ("9999110001", "DE:41"),
        # Method 42 with a wrong check digit.
        ("0000059499", "DE:42"),
        # Method 43 with a wrong check digit.
        ("9516893475", "DE:43"),
        # Method 44 with a wrong check digit.
        ("2618040505", "DE:44"),
        # Valid for method 33, but method 44 expects check digit 6.
        ("0000889008", "DE:44"),
        # Method 46 with a wrong check digit at position 8.
        ("0235468712", "DE:46"),
        # Method 47 with a wrong check digit at position 9.
        ("1003554460", "DE:47"),
        # Neither method 00 (check digit 7) nor method 01 (check digit 9) accepts it.
        ("1234567890", "DE:49"),
        # Method 50 with a wrong check digit at position 7, with and without sub-account.
        ("4000006001", "DE:50"),
        ("0004000006", "DE:50"),
        # Shifting only applies to three leading zeros, it would drop the 1 here.
        ("0014444442", "DE:50"),
        # Method 76 only accepts leading digits 0, 4, 6, 7, 8 and 9.
        ("1234567890", "DE:76"),
        ("0000123457", "DE:76"),
        ("1234567890", "DE:A2"),
        ("0123456789", "DE:A2"),
        ("6543217890", "DE:A3"),
        ("0543216789", "DE:A3"),
        # Just outside the exception range of method 99 the check digit applies again.
        ("0395999999", "DE:99"),
        ("0500000000", "DE:99"),
        # Method 95 test account numbers with a wrong check digit.
        ("0068007004", "DE:95"),
        ("6454000004", "DE:95"),
        # Just outside the exception ranges of method 95 the check digit applies.
        ("0002000000", "DE:95"),
        ("0008999999", "DE:95"),
        ("0026000000", "DE:95"),
        ("0395999999", "DE:95"),
        ("0500000000", "DE:95"),
        ("0699999999", "DE:95"),
        ("0800000000", "DE:95"),
        ("0909999999", "DE:95"),
        ("0990000001", "DE:95"),
        # Method C1 test account numbers with a wrong check digit, variant 1.
        ("0446786240", "DE:C1"),
        ("0478046340", "DE:C1"),
        ("0701625730", "DE:C1"),
        ("0701625440", "DE:C1"),
        ("0882095130", "DE:C1"),
        # Method C1 test account numbers with a wrong check digit, variant 2.
        ("5432112341", "DE:C1"),
        ("5543223458", "DE:C1"),
        ("5654334565", "DE:C1"),
        ("5765445672", "DE:C1"),
        ("5876556780", "DE:C1"),
        # The leading digit picks the variant and the other one is never tried:
        # 5478046940 passes method 17 but starts with 5, 0543223450 passes variant 2
        # but does not.
        ("5478046940", "DE:C1"),
        ("0543223450", "DE:C1"),
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


def test_german_checksum_31_invalid_remainder() -> None:
    # 1*1 + 1*9 = 10, and a remainder of 10 makes the account code invalid whatever the
    # check digit is.
    algo = algorithms["DE:31"]
    with pytest.raises(InvalidBBANChecksum, match="Invalid remainder"):
        algo.validate(["1000000010"], "")
    assert algo.solve(["1000000010"]) is None


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


@pytest.mark.parametrize("algorithm_name", ["DE:49", "DE:A2", "DE:A3"])
def test_german_checksum_fallback_variants_compute_and_solve(algorithm_name: str) -> None:
    # Variant 1 (method 00) can always place a check digit, so it is used for all of them.
    algo = algorithms[algorithm_name]
    assert algo.compute(["3456789010"]) == "9"
    assert algo.solve(["3456789010"]) == ["3456789019"]


def test_german_checksum_48_compute_and_solve() -> None:
    algo = algorithms["DE:48"]
    assert algo.compute(["1234567890"]) == "1"
    assert algo.solve(["1234567890"]) == ["1234567810"]


def test_german_checksum_31_compute_and_solve() -> None:
    algo = algorithms["DE:31"]
    assert algo.compute(["0263160160"]) == "5"
    assert algo.solve(["0263160160"]) == ["0263160165"]


def test_german_checksum_40_compute_and_solve() -> None:
    algo = algorithms["DE:40"]
    assert algo.compute(["0003231960"]) == "3"
    assert algo.solve(["0003231960"]) == ["0003231963"]


def test_german_checksum_41_compute_and_solve() -> None:
    algo = algorithms["DE:41"]
    assert algo.compute(["4019110000"]) == "8"
    assert algo.solve(["4019110000"]) == ["4019110008"]


def test_german_checksum_42_compute_and_solve() -> None:
    algo = algorithms["DE:42"]
    assert algo.compute(["0000059490"]) == "8"
    assert algo.solve(["0000059490"]) == ["0000059498"]


def test_german_checksum_43_compute_and_solve() -> None:
    algo = algorithms["DE:43"]
    assert algo.compute(["9516893470"]) == "6"
    assert algo.solve(["9516893470"]) == ["9516893476"]


def test_german_checksum_44_compute_and_solve() -> None:
    algo = algorithms["DE:44"]
    assert algo.compute(["2618040500"]) == "4"
    assert algo.solve(["2618040500"]) == ["2618040504"]


def test_german_checksum_46_compute_and_solve() -> None:
    algo = algorithms["DE:46"]
    assert algo.compute(["0235468012"]) == "6"
    assert algo.solve(["0235468012"]) == ["0235468612"]


def test_german_checksum_47_compute_and_solve() -> None:
    algo = algorithms["DE:47"]
    assert algo.compute(["1003554400"]) == "5"
    assert algo.solve(["1003554400"]) == ["1003554450"]


def test_german_checksum_50_compute_and_solve() -> None:
    algo = algorithms["DE:50"]
    assert algo.compute(["4444440001"]) == "2"
    assert algo.solve(["4444440001"]) == ["4444442001"]


@pytest.mark.parametrize(
    ("account_code", "check_digit", "solved"),
    [
        # Variant 1 (method 17) places the check digit at position 8.
        ("0446786940", "0", "0446786040"),
        # Variant 2 places it at position 10.
        ("5432112340", "9", "5432112349"),
    ],
)
def test_german_checksum_c1_compute_and_solve(
    account_code: str, check_digit: str, solved: str
) -> None:
    algo = algorithms["DE:C1"]
    assert algo.compute([account_code]) == check_digit
    assert algo.solve([account_code]) == [solved]


@pytest.mark.parametrize(
    ("bank_code", "account_code", "valid"),
    [
        # Variant 1 (method 52) builds the ESER account number from the bank code, and
        # the Bundesbank examples for it are given with bank code 13051172.
        ("13051172", "0043001500", True),
        ("13051172", "0048726458", True),
        ("13051172", "0029837521", False),
        # This one fails variant 1 but passes variant 2 (method 20).
        ("13051172", "0082335729", True),
        # Variant 2 test account numbers.
        ("13051172", "0734192657", True),
        ("13051172", "6932875274", True),
        ("13051172", "0132572975", False),
        ("13051172", "3038752371", False),
        # Variant 1 depends on the bank code, and these fail method 20.
        ("13051042", "0043001500", False),
        ("13051042", "0048726458", False),
    ],
)
def test_german_checksum_c0(bank_code: str, account_code: str, valid: bool) -> None:
    assert algorithms["DE:C0"].validate([bank_code, account_code], "") is valid


def test_german_checksum_c0_compute_and_solve() -> None:
    algo = algorithms["DE:C0"]
    # The method 52 example: bank code 13051172 and account code 4P001500 give P = 3.
    assert algo.compute(["13051172", "0040001500"]) == "3"
    assert algo.compute(["13051172", "1234567890"]) == "6"
    # The check digit is solved with method 20, which accepts every account code.
    assert algo.solve(["13051172", "1234567890"]) == ["13051172", "1234567896"]


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
