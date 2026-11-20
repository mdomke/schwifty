from typing import ClassVar

import pytest

from schwifty import checksum
from schwifty._compat import override
from schwifty.checksum import algorithms
from schwifty.checksum.germany import AcceptedRanges
from schwifty.checksum.germany import Algorithm00
from schwifty.checksum.germany import Algorithm02
from schwifty.checksum.germany import Algorithm09
from schwifty.checksum.germany import Algorithm91
from schwifty.checksum.germany import Algorithm98
from schwifty.checksum.germany import AlgorithmC0
from schwifty.checksum.germany import digit_sum
from schwifty.checksum.germany import FallbackVariants
from schwifty.checksum.germany import SelectedVariant
from schwifty.checksum.germany import WeightedModulus
from schwifty.domain import Component
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
        # Method 23 compares positions 6 and 7 instead.
        ("0000066012", "DE:23"),
        ("0012345008", "DE:10"),
        ("0087654008", "DE:10"),
        ("1000000060", "DE:11"),
        # Remainder 1 would be check digit 10; method 11 maps that to 9.
        ("0000000069", "DE:11"),
        ("0123456600", "DE:13"),
        ("0001234566", "DE:13"),
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
        # Method 27 test account numbers. Numbers >= 1 000 000 000 use method 29 (iterated
        # transformation); numbers < 1 000 000 000 use method 00.
        ("0009290701", "DE:27"),
        ("0539290858", "DE:27"),
        ("2847169488", "DE:27"),
        ("6019937007", "DE:27"),
        ("6021354007", "DE:27"),
        # Method 29 test account numbers (iterated transformation).
        ("1000061378", "DE:29"),
        ("1000061412", "DE:29"),
        ("2938692523", "DE:29"),
        ("3145863029", "DE:29"),
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
        ("0012345600", "DE:76"),
        ("0006543200", "DE:76"),
        ("9012345600", "DE:76"),
        ("7876543100", "DE:76"),
        # A remainder of 10 leaves no check digit at position 8, but the sub-account
        # may still be omitted, with check digit 9 at position 10.
        ("0000005009", "DE:76"),
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
        # Method A7 test account numbers. Variant 1 is method 00, and the account codes it
        # rejects are checked with method 03, which adds the products without their digit
        # sums. For 0019010660, method 00 counts 6*2 = 12 as 1 + 2 and expects check digit 9,
        # method 03 adds 12 and expects 0.
        ("0019010008", "DE:A7"),
        ("0019010438", "DE:A7"),
        ("0019010660", "DE:A7"),
        ("0019010876", "DE:A7"),
        ("0209010892", "DE:A7"),
        # Method B2 test account numbers. Account codes starting with 0 to 7 are checked with
        # method 02 (variant 1), those starting with 8 or 9 with method 00 (variant 2).
        ("0020012357", "DE:B2"),
        ("0080012345", "DE:B2"),
        ("0926801910", "DE:B2"),
        ("1002345674", "DE:B2"),
        ("8000990054", "DE:B2"),
        ("9000481805", "DE:B2"),
        # Method B3 test account numbers. Account codes starting with 0 to 8 are checked with
        # method 32 (variant 1), those starting with 9 with method 06 (variant 2).
        ("0000000019", "DE:B3"),
        ("0000000140", "DE:B3"),
        ("1000000060", "DE:B3"),
        ("1002798417", "DE:B3"),
        ("8409915001", "DE:B3"),
        ("9635000101", "DE:B3"),
        ("9730200100", "DE:B3"),
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
        # Method D8 test account numbers. From 1000000000 on, variant 1 (method 00) applies.
        ("1403414848", "DE:D8"),
        ("6800000439", "DE:D8"),
        ("6899999954", "DE:D8"),
        # Variant 2 (method 09) accepts the whole range 0010000000 to 0099999999 without a check.
        ("0010000000", "DE:D8"),
        ("0099999999", "DE:D8"),
        # Method 99 accepts the whole range 0396000000 to 0499999999 without a check.
        ("0396000001", "DE:99"),
        ("0412345678", "DE:99"),
        # Method 08 applies no check digit below account number 60000, so an
        # account in [6000, 60000) is valid regardless of its check digit.
        ("0000006000", "DE:08"),
        ("0000059999", "DE:08"),
        # Method 30 has no test account numbers, so these are computed by hand.
        ("1234567892", "DE:30"),
        ("9876543218", "DE:30"),
        # Method 56 examples. Account codes starting with 9 use the check digit 7 for a
        # result of 10 and 8 for a result of 11.
        ("0290545005", "DE:56"),
        ("9718304037", "DE:56"),
        ("9000000048", "DE:56"),
        # Method 59 does not check account codes with fewer than nine digits.
        ("0012345678", "DE:59"),
        ("0539290858", "DE:59"),
        # Method 64 test account numbers.
        ("1206473010", "DE:64"),
        ("5016511020", "DE:64"),
        # Method 65 examples. With a 9 at position 9, positions 9 and 10 count too.
        ("1234567400", "DE:65"),
        ("1234567590", "DE:65"),
        # Method 66 test account numbers. Remainder 0 gives the check digit 1, and
        # account codes with 9 at position 2 are not checked.
        ("0100154508", "DE:66"),
        ("0101154508", "DE:66"),
        ("0100154516", "DE:66"),
        ("0101154516", "DE:66"),
        ("0100000021", "DE:66"),
        ("0983393104", "DE:66"),
        # Method 67 has no test account numbers. The sub-account at positions 9 and 10
        # does not count.
        ("1234567400", "DE:67"),
        ("1234567499", "DE:67"),
        # Method 71 example. Remainder 1 gives the check digit 1.
        ("7101234007", "DE:71"),
        ("0100006001", "DE:71"),
        # Method 78 test account numbers. 8-digit account codes are not checked.
        ("0007581499", "DE:78"),
        ("9999999981", "DE:78"),
        ("0012345678", "DE:78"),
        # Method 92 has no test account numbers.
        ("1234567893", "DE:92"),
        # Method 94 test account number.
        ("6782533003", "DE:94"),
        # Method D7 test account numbers.
        ("0500018205", "DE:D7"),
        ("0230103715", "DE:D7"),
        ("0301000434", "DE:D7"),
        ("0330035104", "DE:D7"),
        ("0420001202", "DE:D7"),
        ("0134637709", "DE:D7"),
        ("0201005939", "DE:D7"),
        ("0602006999", "DE:D7"),
        # Method E0 test account numbers.
        ("1234568013", "DE:E0"),
        ("1534568010", "DE:E0"),
        ("0002610015", "DE:E0"),
        ("8741013011", "DE:E0"),
        # Method 96 test account numbers.
        ("0000254100", "DE:96"),
        ("9421000009", "DE:96"),
        ("0000000208", "DE:96"),
        ("0101115152", "DE:96"),
        ("0301204301", "DE:96"),
        # Method 98 test account numbers.
        ("9619439213", "DE:98"),
        ("9619509976", "DE:98"),
        ("9619319999", "DE:98"),
        ("3009800016", "DE:98"),
        ("5989800173", "DE:98"),
        ("6719430018", "DE:98"),
        ("9619608118", "DE:98"),
        # Method B1 test account numbers.
        ("1434253150", "DE:B1"),
        ("2746315471", "DE:B1"),
        ("7414398260", "DE:B1"),
        ("8347251693", "DE:B1"),
        ("0001501824", "DE:B1"),
        ("0001501832", "DE:B1"),
        ("0539290858", "DE:B1"),
        ("7414398268", "DE:B1"),
        ("8347251699", "DE:B1"),
        # Method B8 test account numbers.
        ("0734192657", "DE:B8"),
        ("6932875274", "DE:B8"),
        ("3145863029", "DE:B8"),
        ("2938692523", "DE:B8"),
        ("5100000000", "DE:B8"),
        ("9109999999", "DE:B8"),
        ("5432198760", "DE:B8"),
        ("9070873333", "DE:B8"),
        # Method C2 test account numbers.
        ("2394871426", "DE:C2"),
        ("4218461950", "DE:C2"),
        ("7352569148", "DE:C2"),
        ("5127485166", "DE:C2"),
        ("8738142564", "DE:C2"),
        ("0076543216", "DE:C2"),
        ("3456789012", "DE:C2"),
        ("9024675138", "DE:C2"),
        # Method C7 test account numbers.
        ("0003500022", "DE:C7"),
        ("0038150900", "DE:C7"),
        ("0600103660", "DE:C7"),
        ("0039101181", "DE:C7"),
        ("0094012341", "DE:C7"),
        ("5073321010", "DE:C7"),
        # Method C8 test account numbers.
        ("3456789019", "DE:C8"),
        ("5678901231", "DE:C8"),
        ("3456789012", "DE:C8"),
        ("0022007130", "DE:C8"),
        ("0123456789", "DE:C8"),
        ("0552071285", "DE:C8"),
        # Method C9 test account numbers.
        ("3456789019", "DE:C9"),
        ("5678901231", "DE:C9"),
        ("0123456789", "DE:C9"),
        # Method D2 test account numbers.
        ("0189912137", "DE:D2"),
        ("0235308215", "DE:D2"),
        ("4455667784", "DE:D2"),
        ("1234567897", "DE:D2"),
        ("0051181008", "DE:D2"),
        ("0071214205", "DE:D2"),
        # Method D6 test account numbers.
        ("0000003409", "DE:D6"),
        ("0000585327", "DE:D6"),
        ("0001650513", "DE:D6"),
        ("3601671056", "DE:D6"),
        ("4402001046", "DE:D6"),
        ("6100268241", "DE:D6"),
        ("7001000681", "DE:D6"),
        ("9000111105", "DE:D6"),
        ("9001291005", "DE:D6"),
        # Method E3 test account numbers.
        ("0009290701", "DE:E3"),
        ("0539290858", "DE:E3"),
        ("0001501824", "DE:E3"),
        ("0001501832", "DE:E3"),
        ("0009290708", "DE:E3"),
        ("0539290854", "DE:E3"),
        ("0001501823", "DE:E3"),
        ("0001501831", "DE:E3"),
        ("2345678909", "DE:E3"),
        ("5678901237", "DE:E3"),
        # Method E4 test account numbers.
        ("0001501836", "DE:E4"),
        ("0009290702", "DE:E4"),
        ("0539290858", "DE:E4"),
        ("0001501824", "DE:E4"),
        ("0001501832", "DE:E4"),
        ("0009290701", "DE:E4"),
        # Method 74 test account numbers.
        ("0000001016", "DE:74"),
        ("0000026260", "DE:74"),
        ("0000242243", "DE:74"),
        ("0000242248", "DE:74"),
        ("0018002113", "DE:74"),
        ("1821200043", "DE:74"),
        ("0000001015", "DE:74"),
        ("0000026263", "DE:74"),
        ("0000242241", "DE:74"),
        ("0018002116", "DE:74"),
        ("1821200047", "DE:74"),
        ("3456789012", "DE:74"),
        # Method A5 test account numbers.
        ("9941510001", "DE:A5"),
        ("9961230019", "DE:A5"),
        ("9380027210", "DE:A5"),
        ("9932290910", "DE:A5"),
        ("0000251437", "DE:A5"),
        ("0007948344", "DE:A5"),
        ("0000159590", "DE:A5"),
        ("0000051640", "DE:A5"),
        # Method A6 test account numbers.
        ("0800048548", "DE:A6"),
        ("0855000014", "DE:A6"),
        ("0000000017", "DE:A6"),
        ("0055300030", "DE:A6"),
        ("0150178033", "DE:A6"),
        ("0600003555", "DE:A6"),
        ("0900291823", "DE:A6"),
        # Method B5 test account numbers.
        ("0159006955", "DE:B5"),
        ("2000123451", "DE:B5"),
        ("1151043216", "DE:B5"),
        ("9000939033", "DE:B5"),
        ("0123456782", "DE:B5"),
        ("0130098767", "DE:B5"),
        ("1045000252", "DE:B5"),
        ("1151043211", "DE:B5"),
        # Method B7 test account numbers.
        ("0700001529", "DE:B7"),
        ("0730000019", "DE:B7"),
        ("0001001008", "DE:B7"),
        ("0001057887", "DE:B7"),
        ("0001007222", "DE:B7"),
        ("0810011825", "DE:B7"),
        ("0800107653", "DE:B7"),
        ("0005922372", "DE:B7"),
        ("0000999999", "DE:B7"),
        ("0006000000", "DE:B7"),
        ("0699999999", "DE:B7"),
        ("0900000000", "DE:B7"),
        # Method D0 test account numbers.
        ("6100272324", "DE:D0"),
        ("6100273479", "DE:D0"),
        ("5700000000", "DE:D0"),
        ("5799999999", "DE:D0"),
        # Method 51 test account numbers.
        ("0001156071", "DE:51"),
        ("0001156136", "DE:51"),
        ("0001156078", "DE:51"),
        ("0001234567", "DE:51"),
        ("0000340968", "DE:51"),
        ("0000201178", "DE:51"),
        ("0001009588", "DE:51"),
        ("0000156071", "DE:51"),
        ("0101356073", "DE:51"),
        ("0199100002", "DE:51"),
        ("0099100010", "DE:51"),
        ("2599100002", "DE:51"),
        ("0199100004", "DE:51"),
        ("2599100003", "DE:51"),
        ("3199204090", "DE:51"),
        # Method 57 test account numbers.
        ("7500021766", "DE:57"),
        ("9400001734", "DE:57"),
        ("7800028282", "DE:57"),
        ("8100244186", "DE:57"),
        ("3251080371", "DE:57"),
        ("3891234567", "DE:57"),
        ("7777778800", "DE:57"),
        ("5001050352", "DE:57"),
        ("5045090090", "DE:57"),
        ("1909700805", "DE:57"),
        ("9322111030", "DE:57"),
        ("7400060823", "DE:57"),
        ("0185125434", "DE:57"),
        # Method 58 test account numbers.
        ("1800881120", "DE:58"),
        ("9200654108", "DE:58"),
        ("1015222224", "DE:58"),
        ("3703169668", "DE:58"),
        ("1800293377", "DE:58"),
        # Method 81 test account numbers.
        ("0000646440", "DE:81"),
        ("0001359100", "DE:81"),
        ("0199100002", "DE:81"),
        ("0099100010", "DE:81"),
        ("2599100002", "DE:81"),
        ("0199100004", "DE:81"),
        ("2599100003", "DE:81"),
        ("3199204090", "DE:81"),
        # Method 93 test account numbers.
        ("6714790000", "DE:93"),
        ("0000671479", "DE:93"),
        ("1277830000", "DE:93"),
        ("0000127783", "DE:93"),
        ("1277910000", "DE:93"),
        ("0000127791", "DE:93"),
        ("3067540000", "DE:93"),
        ("0000306754", "DE:93"),
        ("6714791000", "DE:93"),
        # Method A4 test account numbers.
        ("0004711173", "DE:A4"),
        ("0007093330", "DE:A4"),
        ("0004711172", "DE:A4"),
        ("0007093335", "DE:A4"),
        ("1199503010", "DE:A4"),
        ("8499421235", "DE:A4"),
        ("0000862342", "DE:A4"),
        ("8997710000", "DE:A4"),
        ("0664040000", "DE:A4"),
        ("0000905844", "DE:A4"),
        ("5030101099", "DE:A4"),
        ("0001123458", "DE:A4"),
        ("1299503117", "DE:A4"),
        # Method A8 test account numbers.
        ("0007436661", "DE:A8"),
        ("0007436670", "DE:A8"),
        ("0001359100", "DE:A8"),
        ("0007436660", "DE:A8"),
        ("0007436678", "DE:A8"),
        ("0003503398", "DE:A8"),
        ("0001340967", "DE:A8"),
        ("0199100002", "DE:A8"),
        ("0099100010", "DE:A8"),
        ("2599100002", "DE:A8"),
        ("0199100004", "DE:A8"),
        ("2599100003", "DE:A8"),
        ("3199204090", "DE:A8"),
        # Method C3 test account numbers.
        ("0009294182", "DE:C3"),
        ("0004431276", "DE:C3"),
        ("0000019919", "DE:C3"),
        ("9000420530", "DE:C3"),
        ("9000010006", "DE:C3"),
        ("9000577650", "DE:C3"),
        # Method C5 test account numbers.
        ("0000301168", "DE:C5"),
        ("0000302554", "DE:C5"),
        ("0300020050", "DE:C5"),
        ("0300566000", "DE:C5"),
        ("1000061378", "DE:C5"),
        ("1000061412", "DE:C5"),
        ("4450164064", "DE:C5"),
        ("4863476104", "DE:C5"),
        ("5000000028", "DE:C5"),
        ("5000000391", "DE:C5"),
        ("6450008149", "DE:C5"),
        ("6800001016", "DE:C5"),
        ("9000100012", "DE:C5"),
        ("9000210017", "DE:C5"),
        ("3060188103", "DE:C5"),
        ("3070402023", "DE:C5"),
        ("0030000000", "DE:C5"),
        ("0059999999", "DE:C5"),
        ("7000000000", "DE:C5"),
        ("7099999999", "DE:C5"),
        ("8500000000", "DE:C5"),
        ("8599999999", "DE:C5"),
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
        ("0000061011", "DE:23"),
        ("0001234567", "DE:13"),
        # Method 63 only accepts a leading zero.
        ("1123456600", "DE:63"),
        # Without the sub-account the check digit at position 10 still has to match.
        ("0001234567", "DE:63"),
        # Method 48 with a wrong check digit at position 9.
        ("1234567890", "DE:48"),
        ("0099999910", "DE:48"),
        # Valid for method 06, but method 48 expects check digit 7 at position 9.
        ("0094012341", "DE:48"),
        # Method 27 with a wrong check digit.
        ("2847169487", "DE:27"),
        ("6025017009", "DE:27"),
        ("6028267003", "DE:27"),
        # Method 29 with a wrong check digit.
        ("0132572975", "DE:29"),
        ("1000061457", "DE:29"),
        ("1000061498", "DE:29"),
        ("5432198760", "DE:29"),
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
        # Method 76 test account numbers with a wrong check digit.
        ("0006543300", "DE:76"),
        ("9012345700", "DE:76"),
        # A remainder of 10 leaves no check digit at position 8, so 0 is not accepted.
        ("9012347000", "DE:76"),
        ("0000005000", "DE:76"),
        ("1234567890", "DE:A2"),
        ("0123456789", "DE:A2"),
        ("6543217890", "DE:A3"),
        ("0543216789", "DE:A3"),
        # Method A7 test account number that neither method 00 nor method 03 accepts.
        ("0209010893", "DE:A7"),
        # Method B2 test account numbers. The leading digit picks the variant and the other
        # one is never tried: these variant 1 numbers pass method 00, and all variant 2
        # numbers but 9980480111 pass method 02.
        ("0080012347", "DE:B2"),
        ("0932100027", "DE:B2"),
        ("3310123454", "DE:B2"),
        ("8000990057", "DE:B2"),
        ("8011000126", "DE:B2"),
        ("9000481800", "DE:B2"),
        ("9980480111", "DE:B2"),
        # Method B3 test account numbers.
        ("0002799899", "DE:B3"),
        ("1000000111", "DE:B3"),
        ("9635100101", "DE:B3"),
        ("9730300100", "DE:B3"),
        # The leading digit picks the B3 variant and the other one is never tried: these
        # account codes only pass method 06 (variant 2) and method 32 (variant 1) respectively.
        ("1000000066", "DE:B3"),
        ("9635000106", "DE:B3"),
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
        # Method D8 test account numbers. 0000260986 is in neither range.
        ("3012084101", "DE:D8"),
        ("1062813622", "DE:D8"),
        ("0000260986", "DE:D8"),
        # Account codes in neither range are invalid, even if they pass method 00.
        ("0009290701", "DE:D8"),
        ("0539290858", "DE:D8"),
        ("1234567890", "DE:30"),
        ("9876543210", "DE:30"),
        ("0290545006", "DE:56"),
        ("9718304038", "DE:56"),
        ("0539290850", "DE:59"),
        ("1206474010", "DE:64"),
        ("5016512020", "DE:64"),
        ("1234567500", "DE:65"),
        ("1234567490", "DE:65"),
        ("0100154509", "DE:66"),
        # Position 1 does not belong to the account number and has to be 0.
        ("1100154508", "DE:66"),
        ("1234567500", "DE:67"),
        ("7101234008", "DE:71"),
        ("0007581498", "DE:78"),
        ("9999999982", "DE:78"),
        ("1234567890", "DE:92"),
        ("6782533004", "DE:94"),
        ("0501006102", "DE:D7"),
        ("0231307867", "DE:D7"),
        ("0301005331", "DE:D7"),
        ("0330034104", "DE:D7"),
        ("0420001302", "DE:D7"),
        ("0135638809", "DE:D7"),
        ("0202005939", "DE:D7"),
        ("0601006977", "DE:D7"),
        ("1234769013", "DE:E0"),
        ("0002710014", "DE:E0"),
        ("9741015011", "DE:E0"),
        ("0123456789", "DE:B1"),
        ("2345678901", "DE:B1"),
        ("5678901234", "DE:B1"),
        ("0132572975", "DE:B8"),
        ("9000412340", "DE:B8"),
        ("9310305011", "DE:B8"),
        ("5099999999", "DE:B8"),
        ("9110000001", "DE:B8"),
        ("0328705282", "DE:C2"),
        ("7352569145", "DE:C2"),
        ("9024675131", "DE:C2"),
        ("1234517892", "DE:C7"),
        ("0987614325", "DE:C7"),
        ("1234567890", "DE:C8"),
        ("9012345678", "DE:C8"),
        ("1234567890", "DE:C9"),
        ("9012345678", "DE:C9"),
        ("0006414241", "DE:D2"),
        ("0179751314", "DE:D2"),
        ("7004017653", "DE:D6"),
        ("9002720007", "DE:D6"),
        ("9017483524", "DE:D6"),
        ("0123456789", "DE:E3"),
        ("2345678901", "DE:E3"),
        ("5678901234", "DE:E3"),
        ("7414398260", "DE:E3"),
        ("0012345007", "DE:E4"),
        ("0087654005", "DE:E4"),
        ("0000001011", "DE:74"),
        ("0000026265", "DE:74"),
        ("0018002118", "DE:74"),
        ("6160000024", "DE:74"),
        ("0000242249", "DE:74"),
        ("1234567890", "DE:74"),
        ("9941510002", "DE:A5"),
        ("9961230020", "DE:A5"),
        ("0000251438", "DE:A5"),
        ("0007948345", "DE:A5"),
        ("0860000817", "DE:A6"),
        ("0810033652", "DE:A6"),
        ("0000305888", "DE:A6"),
        ("0200071280", "DE:A6"),
        ("7414398260", "DE:B5"),
        ("8347251693", "DE:B5"),
        ("2345678901", "DE:B5"),
        ("5678901234", "DE:B5"),
        ("9000293707", "DE:B5"),
        ("0159004165", "DE:B5"),
        ("0023456787", "DE:B5"),
        ("0056789018", "DE:B5"),
        ("3045000333", "DE:B5"),
        ("0001057886", "DE:B7"),
        ("0003815570", "DE:B7"),
        ("0005620516", "DE:B7"),
        ("0740912243", "DE:B7"),
        ("0893524479", "DE:B7"),
        ("6100272885", "DE:D0"),
        ("6100273377", "DE:D0"),
        ("6100274012", "DE:D0"),
        ("0123412345", "DE:51"),
        ("0067493647", "DE:51"),
        ("0099345678", "DE:51"),
        ("0099100110", "DE:51"),
        ("0199100040", "DE:51"),
        ("5302707782", "DE:57"),
        ("6412121212", "DE:57"),
        ("1813499124", "DE:57"),
        ("2206735010", "DE:57"),
        ("0012345678", "DE:57"),
        ("1800293376", "DE:58"),
        ("0099345678", "DE:81"),
        ("0099100110", "DE:81"),
        ("0199100040", "DE:81"),
        ("6714780000", "DE:93"),
        ("0000671478", "DE:93"),
        ("0000399443", "DE:A4"),
        ("0000553313", "DE:A4"),
        ("0007436666", "DE:A8"),
        ("0007436677", "DE:A8"),
        ("0003503391", "DE:A8"),
        ("0001340966", "DE:A8"),
        ("0099345678", "DE:A8"),
        ("0099100110", "DE:A8"),
        ("0199100040", "DE:A8"),
        ("0000017002", "DE:C3"),
        ("0000123451", "DE:C3"),
        ("0000122448", "DE:C3"),
        ("9000734028", "DE:C3"),
        ("9000733227", "DE:C3"),
        ("9000731120", "DE:C3"),
        ("0000302589", "DE:C5"),
        ("0000507336", "DE:C5"),
        ("0302555000", "DE:C5"),
        ("0302589000", "DE:C5"),
        ("1000061457", "DE:C5"),
        ("1000061498", "DE:C5"),
        ("4864446015", "DE:C5"),
        ("4865038012", "DE:C5"),
        ("5000001028", "DE:C5"),
        ("5000001075", "DE:C5"),
        ("6450008150", "DE:C5"),
        ("6542812818", "DE:C5"),
        ("9000110012", "DE:C5"),
        ("9000300310", "DE:C5"),
        ("3081000783", "DE:C5"),
        ("3081308871", "DE:C5"),
        ("0029999999", "DE:C5"),
        ("0060000000", "DE:C5"),
        ("7100000000", "DE:C5"),
        ("8499999999", "DE:C5"),
        ("2000000000", "DE:C5"),
        ("0001234567", "DE:C5"),
        ("0000999999", "DE:C5"),
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


def test_norway_checksum_interbank_account_series() -> None:
    # Accounts with the account series 00 weight all ten digits, including the bank register
    # number, like any other account (#356).
    assert algorithms["NO:default"].compute(["1204", "001234"]) == "4"
    assert algorithms["NO:default"].validate(["1204", "001234"], "4") is True
    assert algorithms["NO:default"].validate(["1204", "001234"], "3") is False


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


def test_german_checksum_76_invalid_remainder() -> None:
    # 1*6 + 2*5 + 3*4 + 4*3 + 7*2 = 54 leaves a remainder of 10 for the Stammnummer
    # 012347, so there is no check digit for it, whether the sub-account is left out or not.
    algo = algorithms["DE:76"]
    with pytest.raises(InvalidBBANChecksum, match="Invalid remainder"):
        algo.validate(["0000123470"], "")
    assert algo.solve(["9012347000"]) is None


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


@pytest.mark.parametrize("algorithm_name", ["DE:49", "DE:A2", "DE:A3", "DE:A7"])
def test_german_checksum_fallback_variants_compute_and_solve(algorithm_name: str) -> None:
    # Variant 1 (method 00) can always place a check digit, so it is used for all of them.
    algo = algorithms[algorithm_name]
    assert algo.compute(["3456789010"]) == "9"
    assert algo.solve(["3456789010"]) == ["3456789019"]


@pytest.mark.parametrize(
    "algorithm_name",
    [
        "DE:96",
        "DE:98",
        "DE:B1",
        "DE:B8",
        "DE:C2",
        "DE:C7",
        "DE:C8",
        "DE:C9",
        "DE:D2",
        "DE:D6",
        "DE:E3",
        "DE:E4",
    ],
)
@pytest.mark.parametrize("account_code", ["0000000000", "1234567890", "3456789010", "9876543210"])
def test_german_checksum_chain_solve(algorithm_name: str, account_code: str) -> None:
    algo = algorithms[algorithm_name]
    solved = algo.solve([account_code])
    assert solved is not None
    assert algo.validate(solved, "") is True


@pytest.mark.parametrize("algorithm_name", ["DE:74", "DE:A5", "DE:A6", "DE:B5", "DE:B7", "DE:D0"])
@pytest.mark.parametrize(
    "account_code", ["0000000000", "0000123450", "1234567890", "5712345670", "8876543210"]
)
def test_german_checksum_phase_3_solve(algorithm_name: str, account_code: str) -> None:
    algo = algorithms[algorithm_name]
    solved = algo.solve([account_code])
    assert solved is not None
    assert algo.validate(solved, "") is True


@pytest.mark.parametrize(
    ("account_code", "valid"),
    [
        # The sum is 5, so method 00 gives 5 and rounding up to a multiple of 5 gives 0.
        ("0000100065", True),
        ("0000100060", True),
        # The sum is 10, which already is a multiple of 5, so both rules give 0.
        ("0000100040", True),
        ("0000100045", False),
    ],
)
def test_german_checksum_74_half_decade(account_code: str, valid: bool) -> None:
    assert algorithms["DE:74"].validate([account_code], "") is valid


@pytest.mark.parametrize(
    ("algorithm_name", "account_code"),
    [
        # Method 10 accepts these, but account codes starting with 9 must pass method 00.
        ("DE:A5", "9000000009"),
        # Method 00 accepts these, but account codes starting with 8 or 9 must pass method 05.
        ("DE:B5", "8000000003"),
        ("DE:B5", "9000000100"),
    ],
)
def test_german_checksum_no_fallback(algorithm_name: str, account_code: str) -> None:
    assert algorithms[algorithm_name].validate([account_code], "") is False


@pytest.mark.parametrize(
    ("algorithm_name", "account_code"), [("DE:B7", "0123456789"), ("DE:D0", "5712345678")]
)
def test_german_checksum_selected_method_09(algorithm_name: str, account_code: str) -> None:
    algo = algorithms[algorithm_name]
    assert algo.compute([account_code]) == ""
    assert algo.solve([account_code]) == [account_code]


@pytest.mark.parametrize(
    "algorithm_name",
    ["DE:51", "DE:57", "DE:58", "DE:75", "DE:81", "DE:93", "DE:A4", "DE:A8", "DE:C3", "DE:C5"],
)
def test_german_checksum_phase_4_solve(algorithm_name: str) -> None:
    # Some of these methods reject whole ranges of account codes, so not every input can be
    # solved, but every solution must validate.
    algo = algorithms[algorithm_name]
    account_codes = [
        "0000123450",
        "0001234560",
        "0123450789",
        "0912345089",
        "1234567890",
        "3456789010",
        "5512345670",
        "7012345678",
        "9876543210",
    ]
    solutions = [algo.solve([account_code]) for account_code in account_codes]
    assert any(solved is not None for solved in solutions)
    for solved in solutions:
        if solved is not None:
            assert algo.validate(solved, "") is True


def test_german_checksum_57_variant_4_has_no_check_digit() -> None:
    algo = algorithms["DE:57"]
    assert algo.compute(["1909700805"]) == ""
    assert algo.solve(["1909700805"]) == ["1909700805"]
    assert algo.solve(["1813499124"]) is None


@pytest.mark.parametrize(
    ("account_code", "solved"),
    [
        # 6 and 7 digits: base number at positions 5 to 9, check digit at position 10.
        ("0000123450", "0000123455"),
        ("0001234560", "0001234567"),
        # 9 digits: base number at positions 2 to 6, check digit at position 7.
        ("0123450789", "0123455789"),
        # 9 digits with a 9 at position 2: positions 3 to 7, check digit at position 8.
        ("0912345089", "0912345589"),
    ],
)
def test_german_checksum_75_positions(account_code: str, solved: str) -> None:
    assert algorithms["DE:75"].solve([account_code]) == [solved]


@pytest.mark.parametrize("account_code", ["0000012345", "0012345678", "1234567890"])
def test_german_checksum_75_invalid_length(account_code: str) -> None:
    assert algorithms["DE:75"].validate([account_code], "") is False


@pytest.mark.parametrize(
    ("bank_code", "account_code", "valid"),
    [
        # Method 53, which builds the ESER account number from the bank code.
        ("80053782", "0487310018", True),
        ("80053762", "0467310018", False),
        ("80053772", "0477310018", False),
        # Method 20.
        ("80053762", "9110000000", True),
        ("80053762", "0269876545", True),
        ("80053762", "9111000000", False),
        ("80053762", "0269456780", False),
    ],
)
def test_german_checksum_b6(bank_code: str, account_code: str, valid: bool) -> None:
    assert algorithms["DE:B6"].validate([bank_code, account_code], "") is valid


def test_german_checksum_53() -> None:
    algo = algorithms["DE:53"]
    # The example from the spec.
    assert algo.compute(["16052072", "0382432256"]) == "2"
    assert algo.validate(["16052072", "0382432256"], "") is True
    # 10-digit account codes starting with 9 use method 20.
    assert algo.compute(["16052072", "9123456780"]) == "4"
    assert algo.validate(["16052072", "9123456784"], "") is True
    assert algo.solve(["16052072", "9123456780"]) == ["16052072", "9123456784"]
    # No factor below 10 brings this ESER account number to a remainder of 10.
    assert algo.solve(["16052072", "0100000002"]) is None
    # Account codes with fewer than 9 digits have no ESER account number.
    assert algo.validate(["16052072", "0012345678"], "") is False
    assert algo.solve(["16052072", "0012345678"]) is None
    with pytest.raises(InvalidBBANChecksum):
        algo.compute(["16052072", "0012345678"])


@pytest.mark.parametrize("algorithm_name", ["DE:53", "DE:B6"])
def test_german_checksum_eser_solve(algorithm_name: str) -> None:
    algo = algorithms[algorithm_name]
    solved = algo.solve(["80053782", "0487310010"])
    assert solved == ["80053782", "0483310010"]
    assert algo.validate(["80053782", "0483310010"], "") is True


def test_german_checksum_98_weights_read_from_the_right() -> None:
    # The spec lists the weights 3, 7, 1, ... from left to right. Read from the right,
    # as method 01 applies them, they cycle as 3, 1, 7.
    variant = Algorithm98.Variant1()
    assert variant.validate(["9619439213"], "") is True
    assert variant.validate(["3009800016"], "") is True


def test_german_checksum_fallback_variants_raising_variant_rejects() -> None:
    class RaisingThenAccepting(FallbackVariants):
        variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (Algorithm02, Algorithm09)

    # Method 02 has no check digit for a remainder of 1 and raises, which moves on to the
    # next variant instead of escaping from ``validate``.
    with pytest.raises(InvalidBBANChecksum):
        Algorithm02().compute(["1234567820"])
    assert RaisingThenAccepting().validate(["1234567820"], "") is True
    # Method A2 fails method 00 here, and method 04 raises, so the account code is invalid.
    assert algorithms["DE:A2"].validate(["1234567060"], "") is False


def test_german_checksum_fallback_variants_allows_fallback() -> None:
    class StopsOnNine(FallbackVariants):
        variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (Algorithm00, Algorithm09)

        @override
        def allows_fallback(self, account_code: str) -> bool:
            return account_code[0] != "9"

    # Both account codes fail method 00, but only the one not starting with 9 may fall
    # back to method 09.
    assert StopsOnNine().validate(["1123456781"], "") is True
    assert StopsOnNine().validate(["9123456780"], "") is False


def test_german_checksum_fallback_variants_solve_tries_next_variant() -> None:
    class SmallNumbers(AcceptedRanges):
        ranges: ClassVar[tuple[range, ...]] = (range(1_000),)

    class RangesThenMethod00(FallbackVariants):
        variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (SmallNumbers, Algorithm00)

    algo = RangesThenMethod00()
    assert algo.solve(["0000000123"]) == ["0000000123"]
    # The account code is outside of the range, so method 00 places the check digit.
    assert algo.solve(["1234567890"]) == ["1234567897"]


def test_german_checksum_fallback_variants_picks_components_by_name() -> None:
    checked: list[str] = []

    class SmallNumbers(AcceptedRanges):
        ranges: ClassVar[tuple[range, ...]] = (range(1_000),)

    class BankAndAccount(FallbackVariants):
        accepts: ClassVar[list[Component]] = [Component.BANK_CODE, Component.ACCOUNT_CODE]
        variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (SmallNumbers, Algorithm00)

        @override
        def allows_fallback(self, account_code: str) -> bool:
            checked.append(account_code)
            return True

    algo = BankAndAccount()
    # The variants only accept the account code, so they are given that alone.
    assert algo.validate(["13051172", "1123456780"], "") is True
    assert checked == ["1123456780"]
    assert algo.compute(["13051172", "0000000123"]) == ""
    # The solved account code is put back next to the bank code.
    assert algo.solve(["13051172", "1234567890"]) == ["13051172", "1234567897"]


def test_german_checksum_selected_variant_picks_components_by_name() -> None:
    class BankAndAccount(SelectedVariant):
        accepts: ClassVar[list[Component]] = [Component.BANK_CODE, Component.ACCOUNT_CODE]

        @override
        def get_variant(self, account_code: str) -> checksum.Algorithm:
            return AlgorithmC0() if account_code.startswith("00") else Algorithm00()

    algo = BankAndAccount()
    # Method C0 needs the bank code as well; the Bundesbank example uses 13051172.
    assert algo.validate(["13051172", "0043001500"], "") is True
    assert algo.validate(["13051042", "0043001500"], "") is False
    # Method 00 only accepts the account code.
    assert algo.validate(["13051172", "1123456780"], "") is True
    assert algo.compute(["13051172", "1234567890"]) == "7"
    assert algo.solve(["13051172", "1234567890"]) == ["13051172", "1234567897"]


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
        # Variant 1 (method 02) for account codes starting with 0 to 7.
        ("0020012350", "7", "0020012357"),
        # Variant 2 (method 00) for account codes starting with 8 or 9.
        ("8000990050", "4", "8000990054"),
    ],
)
def test_german_checksum_b2_compute_and_solve(
    account_code: str, check_digit: str, solved: str
) -> None:
    algo = algorithms["DE:B2"]
    assert algo.compute([account_code]) == check_digit
    assert algo.solve([account_code]) == [solved]


@pytest.mark.parametrize("account_code", ["0020012399", "0080012370"])
def test_german_checksum_b2_invalid_remainder(account_code: str) -> None:
    # These variant 1 test account numbers leave a remainder of 1, for which method 02 has
    # no check digit, so they are rejected and can't be solved either.
    algo = algorithms["DE:B2"]
    with pytest.raises(InvalidBBANChecksum, match="Invalid remainder"):
        algo.validate([account_code], "")
    assert algo.solve([account_code]) is None


@pytest.mark.parametrize(
    ("account_code", "check_digit", "solved"),
    [
        # Variant 1 (method 32) for account codes starting with 0 to 8.
        ("1002798410", "7", "1002798417"),
        # Variant 2 (method 06) for account codes starting with 9.
        ("9635000100", "1", "9635000101"),
    ],
)
def test_german_checksum_b3_compute_and_solve(
    account_code: str, check_digit: str, solved: str
) -> None:
    algo = algorithms["DE:B3"]
    assert algo.compute([account_code]) == check_digit
    assert algo.solve([account_code]) == [solved]


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


def test_german_checksum_d8_compute_and_solve() -> None:
    algo = algorithms["DE:D8"]
    # Variant 1 (method 00) places the check digit at position 10.
    assert algo.compute(["6899999950"]) == "4"
    assert algo.solve(["6899999950"]) == ["6899999954"]
    # Variant 2 (method 09) has no check digit, so the account code is left as it is.
    assert algo.compute(["0012345678"]) == ""
    assert algo.solve(["0012345678"]) == ["0012345678"]
    # An account code in neither range has no valid check digit.
    with pytest.raises(InvalidBBANChecksum):
        algo.compute(["0123456789"])
    assert algo.solve(["0123456789"]) is None


@pytest.mark.parametrize(
    ("account_code", "check_digit", "solved"),
    [
        # Method 27: < 1 000 000 000 (Method 00)
        ("0539290850", "8", "0539290858"),
        # Method 27: >= 1 000 000 000 (Method 29)
        ("2847169480", "8", "2847169488"),
    ],
)
def test_german_checksum_27_compute_and_solve(
    account_code: str, check_digit: str, solved: str
) -> None:
    algo = algorithms["DE:27"]
    assert algo.compute([account_code]) == check_digit
    assert algo.solve([account_code]) == [solved]


@pytest.mark.parametrize(
    ("account_code", "check_digit", "solved"),
    [
        ("3145863020", "9", "3145863029"),
        ("2938692520", "3", "2938692523"),
    ],
)
def test_german_checksum_29_compute_and_solve(
    account_code: str, check_digit: str, solved: str
) -> None:
    algo = algorithms["DE:29"]
    assert algo.compute([account_code]) == check_digit
    assert algo.solve([account_code]) == [solved]


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


def test_german_checksum_56_invalid_remainder() -> None:
    # Remainders 0 and 1 give no check digit unless the account code starts with 9.
    algo = algorithms["DE:56"]
    for account_code in ("1000000090", "1000000040"):
        with pytest.raises(InvalidBBANChecksum):
            algo.compute([account_code])
    assert algo.compute(["9000000130"]) == "7"
    assert algo.compute(["9000000040"]) == "8"


def test_german_checksum_66_solve() -> None:
    # Position 1 is set to 0 before solving for the check digit.
    assert algorithms["DE:66"].solve(["1234567890"]) == ["0234567890"]


def test_german_checksum_78_compute_and_solve() -> None:
    algo = algorithms["DE:78"]
    assert algo.compute(["1234567890"]) == "7"
    assert algo.solve(["1234567890"]) == ["1234567897"]
    # 8-digit account codes have no check digit, so they are left as they are.
    assert algo.compute(["0012345678"]) == ""
    assert algo.solve(["0012345678"]) == ["0012345678"]
