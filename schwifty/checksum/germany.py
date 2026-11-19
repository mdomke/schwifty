"""Checksum algorithms for German Bank institutes.

A description of the algorithms can be found on the website of the Bundesbank

https://www.bundesbank.de/resource/blob/603320/16a80c739bbbae592ca575905975c2d0/mL/pruefzifferberechnungsmethoden-data.pdf
"""

from __future__ import annotations

import abc
import string
from contextlib import suppress
from dataclasses import dataclass
from itertools import cycle
from typing import ClassVar

from schwifty import checksum
from schwifty._compat import override
from schwifty.domain import Component
from schwifty.exceptions import InvalidAccountCode
from schwifty.exceptions import InvalidBBANChecksum


ACCOUNT_CODE_LENGTH = 10

register = checksum.register("DE")


@dataclass
class Positions:
    start: int
    end: int
    check_digit: int


def digit_sum(number: int) -> int:
    if number < 10:
        return number
    if number < 100:
        return number // 10 + number % 10
    return sum(int(d) for d in str(number))


def validate_account_code(account_code: str) -> str:
    """Return ``account_code`` if it has the length all German methods expect.

    Methods that look at the account code themselves, before the shared check in
    :meth:`WeightedModulus.get_digits` runs, have to call this first. Otherwise a
    BBAN that is too short to carry an account code leaks a raw ``ValueError`` or
    ``IndexError`` instead of :class:`~schwifty.exceptions.InvalidAccountCode`.
    """
    if len(account_code) != ACCOUNT_CODE_LENGTH:
        raise InvalidAccountCode(
            f"Account code must be {ACCOUNT_CODE_LENGTH} digits long, got {len(account_code)}"
        )
    return account_code


class WeightedModulus(checksum.Algorithm):
    accepts: ClassVar[list[Component]] = [Component.ACCOUNT_CODE]
    minuend: ClassVar[int | None] = None
    modulus: ClassVar[int]
    positions: ClassVar[Positions]
    reverse: ClassVar[bool] = True
    weights: ClassVar[list[int]]

    def __init__(self) -> None:
        self.remainder: int = 0

    @override
    def compute(self, components: list[str]) -> str:
        [account_code] = components
        digits = self.get_digits(self.adjust_input(account_code))
        self.remainder = self.compute_remainder(self.compute_weighted_sum(digits))
        if self.minuend is None:  # noqa: SIM108
            checksum = self.remainder
        else:
            checksum = self.minuend - self.remainder
        return str(self.reconcile(checksum))

    def adjust_input(self, account_code: str) -> str:
        return account_code

    def get_digits(self, account_code: str) -> str:
        validate_account_code(account_code)
        positions = self.get_positions(account_code)
        # The positions are provided as in the specification, which starts counting at 1
        start, end = positions.start - 1, positions.end

        assert start >= 0 and start <= ACCOUNT_CODE_LENGTH  # noqa: PT018
        assert end >= start and end <= ACCOUNT_CODE_LENGTH  # noqa: PT018

        digits = account_code[start:end]
        if self.reverse:
            digits = digits[::-1]
        return digits

    def get_positions(self, account_code: str) -> Positions:
        return self.positions

    def compute_weighted_sum(self, digits: str) -> int:
        return sum(self.compute_summand(int(d), w) for d, w in zip(digits, cycle(self.weights)))

    def compute_summand(self, digit: int, weight: int) -> int:
        return digit * weight

    def compute_remainder(self, number: int) -> int:
        return number % self.modulus

    def reconcile(self, checksum: int) -> int:
        return 0 if checksum >= 10 else checksum

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        account_code = self.adjust_input(components[0])
        check_digit = self.compute(components)
        positions = self.get_positions(account_code)
        return check_digit == account_code[positions.check_digit - 1]

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        # The check digit sits at a fixed position inside the 10-digit account
        # code, so there is exactly one unknown to determine. Try every possible
        # value at that position and keep the one the method accepts, using the
        # existing ``validate`` as the oracle so per-method quirks (exception
        # ranges, special-case reconciliations) are honoured without duplicating
        # their logic. ``None`` signals that this random account body cannot be
        # made valid (e.g. methods that reject a whole class of inputs).
        account_code = validate_account_code(components[0])
        index = self.get_positions(account_code).check_digit - 1
        for digit in string.digits:
            candidate = account_code[:index] + digit + account_code[index + 1 :]
            try:
                if self.validate([candidate], ""):
                    return [candidate]
            except InvalidBBANChecksum:
                continue
        return None


class WeightedMod10(WeightedModulus):
    modulus: ClassVar[int] = 10
    minuend: ClassVar[int | None] = 10


class WeightedMod11(WeightedModulus):
    modulus: ClassVar[int] = 11
    minuend: ClassVar[int | None] = 11


@register
class Algorithm00(WeightedMod10):
    name: ClassVar[str] = "00"
    positions: ClassVar[Positions] = Positions(start=1, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 1]

    @override
    def compute_summand(self, digit: int, weight: int) -> int:
        return digit_sum(super().compute_summand(digit, weight))


@register
class Algorithm01(WeightedMod10):
    name: ClassVar[str] = "01"
    positions: ClassVar[Positions] = Positions(start=1, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [3, 7, 1]


@register
class Algorithm02(WeightedMod11):
    name: ClassVar[str] = "02"
    positions: ClassVar[Positions] = Positions(start=1, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8, 9]

    @override
    def reconcile(self, checksum: int) -> int:
        if self.remainder == 0:
            return 0
        if self.remainder == 1:
            raise InvalidBBANChecksum(f"Invalid remainder: {self.remainder}")
        return checksum


@register
class Algorithm03(Algorithm01):
    name = "03"
    weights: ClassVar[list[int]] = [2, 1]


@register
class Algorithm04(Algorithm02):
    name = "04"
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7]


@register
class Algorithm05(Algorithm01):
    name = "05"
    weights: ClassVar[list[int]] = [7, 3, 1]


@register
class Algorithm06(WeightedMod11):
    name = "06"
    positions = Positions(start=1, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7]


@register
class Algorithm07(Algorithm02):
    name = "07"
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8, 9, 10]


@register
class Algorithm08(Algorithm00):
    name = "08"
    min_account_code = 60000

    @override
    def compute(self, components: list[str]) -> str:
        account_code = validate_account_code(components[0])
        if int(account_code) < self.min_account_code:
            return ""
        return super().compute(components)

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        account_code = validate_account_code(components[0])
        if int(account_code) < self.min_account_code:
            return True
        return super().validate(components, expected)


@register
class Algorithm09(checksum.Algorithm):
    name = "09"
    accepts: ClassVar[list[Component]] = [Component.ACCOUNT_CODE]

    @override
    def compute(self, components: list[str]) -> str:
        return ""

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        return True


class AcceptedRanges(checksum.Algorithm):
    """Method 09 for the account codes in :attr:`ranges`, and invalid for all others.

    Account codes in the ranges carry no check digit. This serves as the last variant of
    a :class:`FallbackVariants`, or as the variant a :class:`SelectedVariant` picks for
    the ranges. The ranges are half-open, like Python's :class:`range`.
    """

    accepts: ClassVar[list[Component]] = [Component.ACCOUNT_CODE]
    ranges: ClassVar[tuple[range, ...]]

    @classmethod
    def contains(cls, account_code: str) -> bool:
        number = int(validate_account_code(account_code))
        return any(number in accepted for accepted in cls.ranges)

    @override
    def compute(self, components: list[str]) -> str:
        return ""

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        return self.contains(components[0])

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        return components if self.contains(components[0]) else None


class FallbackVariants(checksum.Algorithm):
    """Check the account code with each variant in turn until one accepts it.

    A variant that raises :class:`~schwifty.exceptions.InvalidBBANChecksum`, e.g. for a
    remainder that yields no check digit, counts as rejecting the account code.
    """

    accepts: ClassVar[list[Component]] = [Component.ACCOUNT_CODE]
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]]

    def allows_fallback(self, account_code: str) -> bool:
        """Return whether ``account_code`` may be checked with the next variant.

        Override this for methods where a rejection by a variant is final for some
        account codes.
        """
        return True

    @override
    def compute(self, components: list[str]) -> str:
        return self.variants[0]().compute(components)

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        for algo_cls in self.variants:
            with suppress(InvalidBBANChecksum):
                if algo_cls().validate(components, expected):
                    return True
            if not self.allows_fallback(components[0]):
                return False
        return False

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        for algo_cls in self.variants:
            solved = algo_cls().solve(components)
            if solved is not None and self.validate(solved, ""):
                return solved
        return None


class SelectedVariant(checksum.Algorithm):
    """Check the account code with the one variant that the account code selects.

    Unlike :class:`FallbackVariants`, an account code rejected by the selected variant is
    invalid and no other variant is tried. Account codes for which :meth:`get_variant`
    returns ``None`` are invalid as well.
    """

    accepts: ClassVar[list[Component]] = [Component.ACCOUNT_CODE]

    @abc.abstractmethod
    def get_variant(self, account_code: str) -> checksum.Algorithm | None:
        pass

    def select(self, components: list[str]) -> checksum.Algorithm | None:
        return self.get_variant(components[self.accepts.index(Component.ACCOUNT_CODE)])

    @override
    def compute(self, components: list[str]) -> str:
        variant = self.select(components)
        if variant is None:
            raise InvalidBBANChecksum(f"Account code matches no variant of method {self.name}")
        return variant.compute(components)

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        variant = self.select(components)
        return variant is not None and variant.validate(components, expected)

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        variant = self.select(components)
        return None if variant is None else variant.solve(components)


@register
class Algorithm10(Algorithm06):
    name = "10"
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8, 9, 10]


@register
class Algorithm11(Algorithm10):
    name = "11"

    @override
    def reconcile(self, checksum: int) -> int:
        if checksum == 10:
            return 9
        return super().reconcile(checksum)


@register
class Algorithm13(Algorithm00):
    name = "13"
    positions = Positions(start=2, end=7, check_digit=8)
    weights: ClassVar[list[int]] = [2, 1]

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        account_code = validate_account_code(components[0])
        if super().validate(components, expected):
            return True
        # The sub-account number "00" may be omitted, which moves the check digit to position 10.
        if account_code.startswith("00"):
            return super().validate([account_code[2:] + "00"], expected)
        return False


@register
class Algorithm14(Algorithm02):
    name = "14"
    positions = Positions(start=4, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7]


@register
class Algorithm15(Algorithm06):
    name = "15"
    positions = Positions(start=6, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5]


@register
class Algorithm16(Algorithm06):
    name = "16"
    positions = Positions(start=1, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7]

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        [account_code] = components
        check_digit = self.compute(components)
        index = self.positions.check_digit - 1
        if self.remainder == 1 and account_code[index - 1] == account_code[index]:
            return True
        return check_digit == account_code[index]


@register
class Algorithm17(WeightedMod11):
    name = "17"
    minuend: ClassVar[int | None] = 10
    positions = Positions(start=2, end=7, check_digit=8)
    reverse: ClassVar[bool] = False
    weights: ClassVar[list[int]] = [1, 2]

    @override
    def compute_weighted_sum(self, digits: str) -> int:
        return super().compute_weighted_sum(digits) - 1

    @override
    def compute_summand(self, digit: int, weight: int) -> int:
        return digit_sum(super().compute_summand(digit, weight))


@register
class Algorithm18(Algorithm01):
    name = "18"
    weights: ClassVar[list[int]] = [3, 9, 7, 1]


@register
class Algorithm19(Algorithm06):
    name = "19"
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8, 9, 1]


@register
class Algorithm20(Algorithm06):
    name = "20"
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8, 9, 3]


@register
class Algorithm21(Algorithm00):
    name = "21"
    weights: ClassVar[list[int]] = [2, 1]

    @override
    def compute_remainder(self, number: int) -> int:
        while number >= 10:
            number = digit_sum(number)
        return number


@register
class Algorithm22(Algorithm01):
    name = "22"
    weights: ClassVar[list[int]] = [3, 1]

    @override
    def compute_summand(self, digit: int, weight: int) -> int:
        return super().compute_summand(digit, weight) % 10


@register
class Algorithm23(Algorithm16):
    name = "23"
    positions = Positions(start=1, end=6, check_digit=7)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7]


@register
class Algorithm24(WeightedMod10):
    name = "24"
    minuend = None
    positions = Positions(start=1, end=9, check_digit=10)
    reverse = False
    weights: ClassVar[list[int]] = [1, 2, 3]

    @override
    def get_digits(self, account_code: str) -> str:
        digits = super().get_digits(account_code)
        if int(digits[0]) in {3, 4, 5, 6}:
            digits = digits[1:]
        elif int(digits[0]) == 9:
            digits = digits[3:]
        return digits.lstrip("0")

    @override
    def compute_summand(self, digit: int, weight: int) -> int:
        return (super().compute_summand(digit, weight) + weight) % 11


@register
class Algorithm25(WeightedMod11):
    name = "25"
    positions = Positions(start=2, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8, 9]

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        result = super().validate(components, expected)
        [account_code] = components
        if self.remainder == 1 and account_code[1] not in {"8", "9"}:
            return False
        return result


@register
class Algorithm26(Algorithm06):
    name = "26"
    positions = Positions(start=1, end=7, check_digit=8)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7]

    @override
    def adjust_input(self, account_code: str) -> str:
        if account_code.startswith("00"):
            account_code = account_code[2:] + "00"
        return account_code


@register
class Algorithm27(SelectedVariant):
    """Method 00 for account codes up to 999 999 999, method 29 from 1 000 000 000."""

    name = "27"

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm:
        if int(validate_account_code(account_code)) >= 1_000_000_000:
            return Algorithm29()
        return Algorithm00()


@register
class Algorithm28(Algorithm06):
    name = "28"
    positions = Positions(start=1, end=7, check_digit=8)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8]


@register
class Algorithm29(checksum.Algorithm):
    """Iterated transformation table lookup (Modulus 10)."""

    name = "29"
    accepts: ClassVar[list[Component]] = [Component.ACCOUNT_CODE]

    # Transformation table rows 1-4 for digits 0-9
    table: ClassVar[list[list[int]]] = [
        [0, 1, 5, 9, 3, 7, 4, 8, 2, 6],
        [0, 1, 7, 6, 9, 8, 3, 2, 5, 4],
        [0, 1, 8, 4, 6, 2, 9, 5, 7, 3],
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    ]
    # Rows assigned to positions 1 to 9 (from left to right)
    rows: ClassVar[list[int]] = [1, 4, 3, 2, 1, 4, 3, 2, 1]

    @override
    def compute(self, components: list[str]) -> str:
        account_code = validate_account_code(components[0])
        total = sum(
            self.table[row - 1][int(d)] for row, d in zip(self.rows, account_code[:9], strict=True)
        )
        return str((10 - (total % 10)) % 10)

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        account_code = validate_account_code(components[0])
        return self.compute(components) == account_code[9]

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        account_code = validate_account_code(components[0])
        return [account_code[:9] + self.compute([account_code])]


@register
class Algorithm31(WeightedMod11):
    name = "31"
    minuend = None
    positions = Positions(start=1, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [9, 8, 7, 6, 5, 4, 3, 2, 1]

    @override
    def reconcile(self, checksum: int) -> int:
        # The remainder is the check digit, so there is none for a remainder of 10.
        if self.remainder == 10:
            raise InvalidBBANChecksum(f"Invalid remainder: {self.remainder}")
        return checksum


@register
class Algorithm32(Algorithm06):
    name = "32"
    positions = Positions(start=4, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7]


@register
class Algorithm33(Algorithm06):
    name = "33"
    positions = Positions(start=5, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6]


@register
class Algorithm34(Algorithm06):
    name = "34"
    positions = Positions(start=1, end=7, check_digit=8)
    weights: ClassVar[list[int]] = [2, 4, 8, 5, 10, 9, 7]


@register
class Algorithm38(Algorithm06):
    name = "38"
    positions = Positions(start=4, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 4, 8, 5, 10, 9]


@register
class Algorithm40(Algorithm06):
    name = "40"
    weights: ClassVar[list[int]] = [2, 4, 8, 5, 10, 9, 7, 3, 6]


@register
class Algorithm41(Algorithm00):
    name = "41"

    @override
    def get_positions(self, account_code: str) -> Positions:
        # Positions 1 to 3 are not part of the calculation if position 4 is a 9.
        if account_code[3] == "9":
            return Positions(start=4, end=9, check_digit=10)
        return super().get_positions(account_code)


@register
class Algorithm42(Algorithm06):
    name = "42"
    positions = Positions(start=2, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8, 9]


@register
class Algorithm43(Algorithm01):
    name = "43"
    weights: ClassVar[list[int]] = [1, 2, 3, 4, 5, 6, 7, 8, 9]


@register
class Algorithm44(Algorithm06):
    name = "44"
    positions = Positions(start=5, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 4, 8, 5, 10]


@register
class Algorithm46(Algorithm06):
    name = "46"
    positions = Positions(start=3, end=7, check_digit=8)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6]


@register
class Algorithm47(Algorithm06):
    name = "47"
    positions = Positions(start=4, end=8, check_digit=9)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6]


@register
class Algorithm48(Algorithm06):
    name = "48"
    positions = Positions(start=3, end=8, check_digit=9)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7]


@register
class Algorithm50(Algorithm06):
    name = "50"
    positions = Positions(start=1, end=6, check_digit=7)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7]

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        account_code = validate_account_code(components[0])
        if super().validate(components, expected):
            return True
        # The sub-account number "000" may be omitted and the account code padded with
        # leading zeros instead. Shift the account code three positions to the left and
        # check it again.
        if account_code.startswith("000"):
            return super().validate([account_code[3:] + "000"], expected)
        return False


@register
class Algorithm60(Algorithm00):
    name = "60"
    positions = Positions(start=3, end=9, check_digit=10)


@register
class Algorithm61(Algorithm00):
    name = "61"
    positions = Positions(start=1, end=7, check_digit=8)
    weights: ClassVar[list[int]] = [2, 1]

    @override
    def get_digits(self, account_code: str) -> str:
        digits = super().get_digits(account_code)
        if account_code[8] == "8":
            digits = account_code[:7:-1] + digits
        return digits


@register
class Algorithm63(WeightedMod10):
    name = "63"
    positions = Positions(start=2, end=7, check_digit=8)
    weights: ClassVar[list[int]] = [2, 1]

    @override
    def compute_summand(self, digit: int, weight: int) -> int:
        return digit_sum(super().compute_summand(digit, weight))

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        account_code = validate_account_code(components[0])
        if account_code[0] != "0":
            return False
        if super().validate(components, expected):
            return True
        # The sub-account number "00" may be omitted and the account code padded with
        # leading zeros instead. The check digit then sits at position 10, so shift the
        # account code back into place and check it again.
        if account_code.startswith("000"):
            return super().validate([account_code[2:] + "00"], expected)
        return False

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        # The method only accepts account codes with a leading zero, which the check
        # digit alone cannot supply, so set it before solving for the check digit.
        account_code = validate_account_code(components[0])
        return super().solve(["0" + account_code[1:]])


@register
class Algorithm68(Algorithm00):
    name = "68"
    positions = Positions(start=1, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 1]

    @override
    def get_digits(self, account_code: str) -> str:
        digits = super().get_digits(account_code)
        # The digits are already reversed at this point. The algorithm counts the positions from
        # right to left, so that the 7th position is at index 5, when we consider that the 1st
        # position has already been excluded because it is the check digit.
        digits = digits.rstrip("0")
        if len(digits) == 9:
            if digits[5] != "9":
                raise InvalidBBANChecksum(
                    "10 digit long acccount codes require the 7th digit to be set to 9"
                )
            digits = digits[:6]
        return digits

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        account_code = validate_account_code(components[0])
        if 400_000_000 <= int(account_code) <= 499_999_999:
            return True
        if super().validate(components, expected) is False:
            # If the checksum calculation fails, the algorithm should be executed again, with the
            # 7th and 8th position of the account code removed. Since the positions are counted from
            # right to left, they translate into indices 2 and 3 counting from left.
            check_digit = self.compute([account_code[:2] + "00" + account_code[4:]])
            return check_digit == account_code[self.positions.check_digit - 1]
        return True

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        # A 10-significant-digit account code (no leading zero) requires the 7th
        # position -- index 3 -- to be 9, otherwise ``get_digits`` rejects it. Set it
        # so the leading digit stays free, then solve for the check digit.
        account_code = validate_account_code(components[0])
        if account_code[0] != "0":
            account_code = account_code[:3] + "9" + account_code[4:]
        return super().solve([account_code])


@register
class Algorithm76(WeightedMod11):
    name = "76"
    minuend = None
    positions = Positions(start=2, end=7, check_digit=8)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8]

    @override
    def get_digits(self, account_code: str) -> str:
        digits = super().get_digits(account_code)
        return digits.rstrip("0")

    @override
    def reconcile(self, checksum: int) -> int:
        # The remainder is the check digit, so there is none for a remainder of 10.
        if self.remainder == 10:
            raise InvalidBBANChecksum(f"Invalid remainder: {self.remainder}")
        return checksum

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        account_code = validate_account_code(components[0])
        if int(account_code[0]) not in {0, 4, 6, 7, 8, 9}:
            return False
        # A remainder of 10 only rules out a check digit at position 8, so the account
        # code is still checked without the sub-account below.
        with suppress(InvalidBBANChecksum):
            if super().validate(components, expected):
                return True
        # The sub-account number "00" may be omitted and the account code padded with
        # leading zeros instead, which moves the check digit to position 10.
        if account_code.startswith("00") and int(account_code[2]) in {0, 4, 6, 7, 8, 9}:
            return super().validate([account_code[2:] + "00"], expected)
        return False

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        # The method only accepts certain leading digits, which the check digit alone
        # cannot supply, so coerce it into the allowed set before solving.
        account_code = validate_account_code(components[0])
        if int(account_code[0]) not in {0, 4, 6, 7, 8, 9}:
            account_code = "0" + account_code[1:]
        return super().solve([account_code])


@register
class Algorithm88(Algorithm06):
    name = "88"
    positions = Positions(start=4, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8]

    @override
    def get_positions(self, account_code: str) -> Positions:
        if account_code[2] == "9":
            return Positions(start=3, end=9, check_digit=10)
        return super().get_positions(account_code)


@register
class Algorithm91(FallbackVariants):
    name = "91"

    class Variant1(Algorithm06):
        positions = Positions(start=1, end=6, check_digit=7)
        weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7]

    class Variant2(Variant1):
        weights: ClassVar[list[int]] = [7, 6, 5, 4, 3, 2]

    class Variant3(Variant1):
        positions = Positions(start=1, end=10, check_digit=7)
        weights: ClassVar[list[int]] = [2, 3, 4, 0, 5, 6, 7, 8, 9, 10]

    class Variant4(Variant1):
        weights: ClassVar[list[int]] = [2, 4, 8, 5, 10, 9]

    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Variant1,
        Variant2,
        Variant3,
        Variant4,
    )


@register
class Algorithm95(Algorithm06):
    name = "95"

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        [account_code] = components
        if not account_code:
            return False
        number = int(account_code)
        if (
            1 <= number <= 1_999_999
            or 9_000_000 <= number <= 25_999_999
            or 396_000_000 <= number <= 499_999_999
            or 700_000_000 <= number <= 799_999_999
            or 910_000_000 <= number <= 989_999_999
        ):
            return True
        return super().validate(components, expected)


@register
class Algorithm99(Algorithm06):
    name = "99"

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        account_code = validate_account_code(components[0])
        if 396_000_000 <= int(account_code) <= 499_999_999:
            return True
        return super().validate(components, expected)


@register
class Algorithm49(FallbackVariants):
    name = "49"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm00,
        Algorithm01,
    )


@register
class AlgorithmA2(FallbackVariants):
    name = "A2"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm00,
        Algorithm04,
    )


@register
class AlgorithmA3(FallbackVariants):
    name = "A3"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm00,
        Algorithm10,
    )


@register
class AlgorithmA7(FallbackVariants):
    name = "A7"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm00,
        Algorithm03,
    )


@register
class AlgorithmB2(SelectedVariant):
    """Method 02 for account codes starting with 0 to 7, method 00 for 8 and 9.

    The leading digit selects the variant.
    """

    name = "B2"

    @override
    def get_variant(self, account_code: str) -> WeightedModulus:
        if validate_account_code(account_code)[0] in "89":
            return Algorithm00()
        return Algorithm02()


@register
class AlgorithmB3(SelectedVariant):
    """Method 32 for account codes starting with 0 to 8, method 06 for 9.

    The leading digit selects the variant.
    """

    name = "B3"

    @override
    def get_variant(self, account_code: str) -> WeightedModulus:
        if validate_account_code(account_code)[0] == "9":
            return Algorithm06()
        return Algorithm32()


@register
class AlgorithmC1(SelectedVariant):
    """Method 17, or a variant of it over positions 1-9 for account codes starting with 5."""

    name = "C1"

    class Variant2(Algorithm17):
        positions = Positions(start=1, end=9, check_digit=10)

    @override
    def get_variant(self, account_code: str) -> WeightedModulus:
        if validate_account_code(account_code)[0] == "5":
            return self.Variant2()
        return Algorithm17()


@register
class AlgorithmC0(checksum.Algorithm):
    """Method 52 for account codes with exactly two leading zeros, otherwise method 20.

    Method 52 checks the account number of the former ESER system, which is built from the
    bank code and the account code, so unlike the other German methods this one needs the
    bank code too. An account code rejected by method 52 is checked with method 20 as well.
    """

    name = "C0"
    accepts: ClassVar[list[Component]] = [Component.BANK_CODE, Component.ACCOUNT_CODE]
    eser_weights: ClassVar[list[int]] = [2, 4, 8, 5, 10, 9, 7, 3, 6, 1, 2, 4]

    @staticmethod
    def has_two_leading_zeros(account_code: str) -> bool:
        return account_code.startswith("00") and account_code[2] != "0"

    def compute_eser(self, bank_code: str, account_code: str) -> str:
        """Return the method 52 check digit, or an empty string if there is none."""
        # Bank code XXX5XXXX and account code 00XPXXXXXX give the ESER account number
        # XXXX-XP-XXXXXX, with the leading zeros of the last part dropped.
        tail = account_code[4:].lstrip("0")
        digits = bank_code[4:8] + account_code[2] + "0" + tail
        remainder = (
            sum(int(d) * w for d, w in zip(reversed(digits), self.eser_weights, strict=False)) % 11
        )
        weight = self.eser_weights[len(tail)]
        for check_digit in range(10):
            if (remainder + check_digit * weight) % 11 == 10:
                return str(check_digit)
        return ""

    @override
    def compute(self, components: list[str]) -> str:
        bank_code, account_code = components
        if self.has_two_leading_zeros(validate_account_code(account_code)):
            return self.compute_eser(bank_code, account_code)
        return Algorithm20().compute([account_code])

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        bank_code, account_code = components
        if (
            self.has_two_leading_zeros(validate_account_code(account_code))
            and self.compute_eser(bank_code, account_code) == account_code[3]
        ):
            return True
        return Algorithm20().validate([account_code], expected)

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        # Method 20 applies to every account code and always yields a check digit.
        bank_code, account_code = components
        solved = Algorithm20().solve([account_code])
        return None if solved is None else [bank_code, *solved]


@register
class AlgorithmD8(SelectedVariant):
    """Method 00 from account code 1000000000, method 09 from 0010000000 to 0099999999.

    Account codes in neither range are invalid.
    """

    name = "D8"

    class Variant2(AcceptedRanges):
        ranges: ClassVar[tuple[range, ...]] = (range(10_000_000, 100_000_000),)

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm | None:
        if int(validate_account_code(account_code)) >= 1_000_000_000:
            return Algorithm00()
        if self.Variant2.contains(account_code):
            return self.Variant2()
        return None
