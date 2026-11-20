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


ESER_WEIGHTS = (2, 4, 8, 5, 10, 9, 7, 3, 6, 1, 2, 4)


def eser_check_digit(head: str, tail: str) -> str:
    """Return the check digit of the ESER account number ``head`` + P + ``tail``.

    Methods 52 and 53 check the account number of the former ESER system, which is built
    from the bank code and the account code. The check digit is the factor of the weight
    over P that brings the weighted sum to a remainder of 10 modulo 11. An empty string
    means there is no such factor below 10.
    """
    digits = head + "0" + tail
    remainder = sum(int(d) * w for d, w in zip(reversed(digits), ESER_WEIGHTS, strict=False)) % 11
    weight = ESER_WEIGHTS[len(tail)]
    for check_digit in range(10):
        if (remainder + check_digit * weight) % 11 == 10:
            return str(check_digit)
    return ""


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


class WeightedMod7(WeightedModulus):
    """Modulus 7: the check digit is 7 minus the remainder, and 0 for a remainder of 0."""

    modulus: ClassVar[int] = 7
    minuend: ClassVar[int | None] = 7

    @override
    def reconcile(self, checksum: int) -> int:
        return checksum % 7


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
        return self.contains(self.get_component(components, Component.ACCOUNT_CODE))

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        account_code = self.get_component(components, Component.ACCOUNT_CODE)
        return components if self.contains(account_code) else None


class CompositeAlgorithm(checksum.Algorithm):
    """A method that checks the account code with other methods, its variants.

    A variant may accept other components than the method itself, e.g. only the account
    code while another variant also needs the bank code. Each variant is therefore given
    the components it accepts, picked by name, and the components it solves are put back
    in their place.
    """

    accepts: ClassVar[list[Component]] = [Component.ACCOUNT_CODE]

    def components_for(self, variant: checksum.Algorithm, components: list[str]) -> list[str]:
        return [self.get_component(components, component) for component in variant.accepts]

    def compute_with(self, variant: checksum.Algorithm, components: list[str]) -> str:
        return variant.compute(self.components_for(variant, components))

    def validate_with(
        self, variant: checksum.Algorithm, components: list[str], expected: str
    ) -> bool:
        return variant.validate(self.components_for(variant, components), expected)

    def solve_with(self, variant: checksum.Algorithm, components: list[str]) -> list[str] | None:
        solved = variant.solve(self.components_for(variant, components))
        if solved is None:
            return None
        values = dict(zip(self.accepts, components, strict=True))
        values.update(zip(variant.accepts, solved, strict=True))
        return [values[component] for component in self.accepts]


class FallbackVariants(CompositeAlgorithm):
    """Check the account code with each variant in turn until one accepts it.

    A variant that raises :class:`~schwifty.exceptions.InvalidBBANChecksum`, e.g. for a
    remainder that yields no check digit, counts as rejecting the account code.
    """

    variants: ClassVar[tuple[type[checksum.Algorithm], ...]]

    def allows_fallback(self, account_code: str) -> bool:
        """Return whether ``account_code`` may be checked with the next variant.

        Override this for methods where a rejection by a variant is final for some
        account codes.
        """
        return True

    @override
    def compute(self, components: list[str]) -> str:
        return self.compute_with(self.variants[0](), components)

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        account_code = self.get_component(components, Component.ACCOUNT_CODE)
        for algo_cls in self.variants:
            with suppress(InvalidBBANChecksum):
                if self.validate_with(algo_cls(), components, expected):
                    return True
            if not self.allows_fallback(account_code):
                return False
        return False

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        for algo_cls in self.variants:
            solved = self.solve_with(algo_cls(), components)
            if solved is not None and self.validate(solved, ""):
                return solved
        return None


class SelectedVariant(CompositeAlgorithm):
    """Check the account code with the one variant that the account code selects.

    Unlike :class:`FallbackVariants`, an account code rejected by the selected variant is
    invalid and no other variant is tried. Account codes for which :meth:`get_variant`
    returns ``None`` are invalid as well.
    """

    @abc.abstractmethod
    def get_variant(self, account_code: str) -> checksum.Algorithm | None:
        pass

    def select(self, components: list[str]) -> checksum.Algorithm | None:
        return self.get_variant(self.get_component(components, Component.ACCOUNT_CODE))

    @override
    def compute(self, components: list[str]) -> str:
        variant = self.select(components)
        if variant is None:
            raise InvalidBBANChecksum(f"Account code matches no variant of method {self.name}")
        return self.compute_with(variant, components)

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        variant = self.select(components)
        return variant is not None and self.validate_with(variant, components, expected)

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        variant = self.select(components)
        return None if variant is None else self.solve_with(variant, components)


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
class Algorithm30(WeightedMod10):
    name = "30"
    positions = Positions(start=1, end=9, check_digit=10)
    reverse = False
    weights: ClassVar[list[int]] = [2, 0, 0, 0, 0, 1, 2, 1, 2]


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
class Algorithm51(SelectedVariant):
    """Methods A to D in turn, or the exception for account codes with a 9 at position 3.

    Account codes with a 9 at position 3 are Sachkonten (general ledger accounts). Methods
    81 and A8 check them with the same exception.
    """

    name = "51"

    class Methods(FallbackVariants):
        """Method A (32), B (33), C (00 over positions 4 to 9) and D (modulus 7)."""

        class MethodC(Algorithm00):
            positions = Positions(start=4, end=9, check_digit=10)

        class MethodD(WeightedMod7):
            positions = Positions(start=5, end=9, check_digit=10)
            weights: ClassVar[list[int]] = [2, 3, 4, 5, 6]

        variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
            Algorithm32,
            Algorithm33,
            MethodC,
            MethodD,
        )

    class Sachkonten(FallbackVariants):
        """Modulus 11 over positions 3 to 9, then over positions 1 to 9.

        A remainder of 0 or 1 gives the check digit 0.
        """

        class Variant1(WeightedMod11):
            positions = Positions(start=3, end=9, check_digit=10)
            weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8]

        class Variant2(WeightedMod11):
            positions = Positions(start=1, end=9, check_digit=10)
            weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 8, 9, 10]

        variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (Variant1, Variant2)

    @staticmethod
    def is_sachkonto(account_code: str) -> bool:
        return validate_account_code(account_code)[2] == "9"

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm:
        if self.is_sachkonto(account_code):
            return self.Sachkonten()
        return self.Methods()


@register
class Algorithm53(checksum.Algorithm):
    """Method 52 for 9-digit account codes, method 20 for 10-digit ones starting with 9.

    Like method 52, this checks the account number of the former ESER system, so it needs
    the bank code. Other account codes are invalid.
    """

    name = "53"
    accepts: ClassVar[list[Component]] = [Component.BANK_CODE, Component.ACCOUNT_CODE]

    @staticmethod
    def is_nine_digits(account_code: str) -> bool:
        return account_code[0] == "0" and account_code[1] != "0"

    @staticmethod
    def compute_eser(bank_code: str, account_code: str) -> str:
        # Bank code XXX5XXXX and account code 0XTPXXXXXX give the ESER account number
        # XXTX-XP-XXXXXX, with the leading zeros of the last part dropped.
        head = bank_code[4:6] + account_code[2] + bank_code[7] + account_code[1]
        return eser_check_digit(head, account_code[4:].lstrip("0"))

    @override
    def compute(self, components: list[str]) -> str:
        bank_code, account_code = components
        validate_account_code(account_code)
        if account_code[0] == "9":
            return Algorithm20().compute([account_code])
        if self.is_nine_digits(account_code):
            return self.compute_eser(bank_code, account_code)
        raise InvalidBBANChecksum("Method 53 only checks 9-digit or 10-digit account codes")

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        bank_code, account_code = components
        validate_account_code(account_code)
        if account_code[0] == "9":
            return Algorithm20().validate([account_code], expected)
        if self.is_nine_digits(account_code):
            return self.compute_eser(bank_code, account_code) == account_code[3]
        return False

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        bank_code, account_code = components
        validate_account_code(account_code)
        if account_code[0] == "9":
            solved = Algorithm20().solve([account_code])
            return None if solved is None else [bank_code, *solved]
        if not self.is_nine_digits(account_code):
            return None
        check_digit = self.compute_eser(bank_code, account_code)
        if not check_digit:
            return None
        return [bank_code, account_code[:3] + check_digit + account_code[4:]]


@register
class Algorithm56(WeightedMod11):
    """Modulus 11 where a result of 10 or 11 yields no check digit.

    Account codes starting with 9 use the check digit 7 for a result of 10 and 8 for 11
    instead.
    """

    name = "56"
    positions = Positions(start=1, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7, 2, 3, 4]

    def __init__(self) -> None:
        super().__init__()
        self.starts_with_nine: bool = False

    @override
    def compute(self, components: list[str]) -> str:
        self.starts_with_nine = validate_account_code(components[0])[0] == "9"
        return super().compute(components)

    @override
    def reconcile(self, checksum: int) -> int:
        if checksum < 10:
            return checksum
        if not self.starts_with_nine:
            raise InvalidBBANChecksum(f"Invalid remainder: {self.remainder}")
        return 7 if checksum == 10 else 8


@register
class Algorithm57(SelectedVariant):
    """The first two digits of the account code pick one of four variants.

    Account codes starting with 00 are invalid. Account codes starting with 777777 or 888888,
    and the account code 0185125434, are valid without a check digit.
    """

    name = "57"

    class Variant1(Algorithm00):
        """Method 00 with the weights 1, 2, 1, ... from the left."""

        weights: ClassVar[list[int]] = [1, 2]

    class Variant2(Algorithm00):
        """Method 00 with the check digit at position 3 and the weights 1, 2, ... from the left."""

        positions = Positions(start=1, end=10, check_digit=3)
        reverse = False
        weights: ClassVar[list[int]] = [1, 2]

        @override
        def get_digits(self, account_code: str) -> str:
            digits = super().get_digits(account_code)
            return digits[:2] + digits[3:]

    class Variant4(checksum.Algorithm):
        """No check digit, but positions 3-4 must be 01 to 12 and positions 7-9 below 500."""

        accepts: ClassVar[list[Component]] = [Component.ACCOUNT_CODE]

        @staticmethod
        def is_valid(account_code: str) -> bool:
            return 1 <= int(account_code[2:4]) <= 12 and int(account_code[6:9]) < 500

        @override
        def compute(self, components: list[str]) -> str:
            return ""

        @override
        def validate(self, components: list[str], expected: str) -> bool:
            return self.is_valid(components[0])

        @override
        def solve(self, components: list[str]) -> list[str] | None:
            return components if self.is_valid(components[0]) else None

    variant1_prefixes: ClassVar[frozenset[int]] = frozenset(
        {51, 55, 61, 64, 65, 66, 70, *range(73, 83), 88, 94, 95}
    )
    variant3_prefixes: ClassVar[frozenset[int]] = frozenset({40, 50, 91, 99})

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm | None:
        validate_account_code(account_code)
        prefix = int(account_code[:2])
        if account_code == "0185125434" or account_code.startswith(("777777", "888888")):
            return Algorithm09()
        if prefix == 0:
            return None
        if prefix <= 31:
            return self.Variant4()
        if prefix in self.variant1_prefixes:
            return self.Variant1()
        if prefix in self.variant3_prefixes:
            return Algorithm09()
        return self.Variant2()


@register
class Algorithm58(Algorithm02):
    name = "58"
    positions = Positions(start=5, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6]


@register
class Algorithm59(Algorithm08):
    """Method 08 (method 00 that skips small account codes) with a limit of nine digits."""

    name = "59"
    min_account_code = 100_000_000


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
class Algorithm64(Algorithm06):
    name = "64"
    positions = Positions(start=1, end=6, check_digit=7)
    reverse = False
    weights: ClassVar[list[int]] = [9, 10, 5, 8, 4, 2]


@register
class Algorithm65(Algorithm00):
    """Method 00 over positions 1-7, and over positions 9 and 10 too if position 9 is 9."""

    name = "65"
    positions = Positions(start=1, end=7, check_digit=8)
    reverse = False

    @override
    def get_digits(self, account_code: str) -> str:
        digits = super().get_digits(account_code)
        if account_code[8] == "9":
            digits += account_code[8:]
        return digits


@register
class Algorithm66(WeightedMod11):
    """Modulus 11 over positions 2 and 5-9 of an account code whose position 1 is 0.

    Positions 3 and 4 hold a sub-account number and are weighted with 0. Account codes
    with 9 at position 2 have no check digit and are not checked.
    """

    name = "66"
    positions = Positions(start=2, end=9, check_digit=10)
    weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 0, 0, 7]

    @override
    def reconcile(self, checksum: int) -> int:
        if self.remainder == 0:
            return 1
        if self.remainder == 1:
            return 0
        return checksum

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        account_code = validate_account_code(components[0])
        if account_code[0] != "0":
            return False
        if account_code[1] == "9":
            return True
        return super().validate(components, expected)

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        # Position 1 has to be 0, which the check digit alone cannot supply, so set it
        # before solving for the check digit.
        account_code = validate_account_code(components[0])
        return super().solve(["0" + account_code[1:]])


@register
class Algorithm67(Algorithm00):
    name = "67"
    positions = Positions(start=1, end=7, check_digit=8)


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
class Algorithm71(WeightedMod11):
    name = "71"
    positions = Positions(start=2, end=7, check_digit=10)
    reverse = False
    weights: ClassVar[list[int]] = [6, 5, 4, 3, 2, 1]

    @override
    def reconcile(self, checksum: int) -> int:
        # A remainder of 1 gives 10, of which the tens digit 1 is the check digit.
        if checksum == 10:
            return 1
        return super().reconcile(checksum)


@register
class Algorithm74(FallbackVariants):
    """Method 00 with a second check digit for 6-digit account codes, then method 04."""

    name = "74"

    class Variant1(Algorithm00):
        """Method 00, but 6-digit account codes may also round the sum up to a multiple of 5.

        The difference between the rounded and the original sum is the second check digit.
        The spec doesn't say what happens to a sum that is already a multiple of 5. Rounding
        it up leaves it unchanged, so the second check digit is 0 then.
        """

        @override
        def validate(self, components: list[str], expected: str) -> bool:
            if super().validate(components, expected):
                return True
            [account_code] = components
            if not 100_000 <= int(account_code) <= 999_999:
                return False
            # ``validate`` above computed the remainder of the sum modulo 10, which has the
            # same remainder modulo 5 as the sum itself.
            return account_code[-1] == str(-self.remainder % 5)

    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Variant1,
        Algorithm04,
    )


@register
class Algorithm75(SelectedVariant):
    """Method 00 over a 5-digit base number whose place depends on the account code's length.

    6- and 7-digit account codes have the base number at positions 5 to 9 and the check
    digit at position 10. 9-digit ones have them at positions 2 to 6 and 7, or at 3 to 7
    and 8 if position 2 is 9. Account codes of other lengths are invalid.
    """

    name = "75"

    class Variant1(Algorithm00):
        positions = Positions(start=5, end=9, check_digit=10)

    class Variant2(Algorithm00):
        positions = Positions(start=2, end=6, check_digit=7)

    class Variant3(Algorithm00):
        positions = Positions(start=3, end=7, check_digit=8)

    @override
    def get_variant(self, account_code: str) -> WeightedModulus | None:
        number = int(validate_account_code(account_code))
        if 100_000 <= number < 10_000_000:
            return self.Variant1()
        if 100_000_000 <= number < 1_000_000_000:
            return self.Variant3() if account_code[1] == "9" else self.Variant2()
        return None


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
class Algorithm78(SelectedVariant):
    """Method 00, but 8-digit account codes have no check digit and are not checked."""

    name = "78"

    class Variant2(AcceptedRanges):
        ranges: ClassVar[tuple[range, ...]] = (range(10_000_000, 100_000_000),)

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm:
        if self.Variant2.contains(account_code):
            return self.Variant2()
        return Algorithm00()


@register
class Algorithm81(SelectedVariant):
    """Method 32, or the exception of method 51 for account codes with a 9 at position 3."""

    name = "81"

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm:
        if Algorithm51.is_sachkonto(account_code):
            return Algorithm51.Sachkonten()
        return Algorithm32()


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
class Algorithm92(Algorithm01):
    name = "92"
    positions = Positions(start=4, end=9, check_digit=10)


@register
class Algorithm93(FallbackVariants):
    """Modulus 11, then modulus 7, over a 5-digit customer number.

    The customer number is at positions 5 to 9 with the check digit at position 10 if the
    account code starts with 0000, and at positions 1 to 5 with the check digit at position 6
    otherwise.
    """

    name = "93"

    @staticmethod
    def customer_number_positions(account_code: str) -> Positions:
        if account_code.startswith("0000"):
            return Positions(start=5, end=9, check_digit=10)
        return Positions(start=1, end=5, check_digit=6)

    class Variant1(Algorithm06):
        weights: ClassVar[list[int]] = [2, 3, 4, 5, 6]

        @override
        def get_positions(self, account_code: str) -> Positions:
            return Algorithm93.customer_number_positions(account_code)

    class Variant2(WeightedMod7):
        weights: ClassVar[list[int]] = [2, 3, 4, 5, 6]

        @override
        def get_positions(self, account_code: str) -> Positions:
            return Algorithm93.customer_number_positions(account_code)

    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (Variant1, Variant2)


@register
class Algorithm94(Algorithm00):
    name = "94"
    weights: ClassVar[list[int]] = [1, 2]


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
class Algorithm96(FallbackVariants):
    """Method 19, then method 00, then valid for account codes 0001300000 to 0099399999."""

    name = "96"

    class Variant3(AcceptedRanges):
        ranges: ClassVar[tuple[range, ...]] = (range(1_300_000, 99_400_000),)

    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm19,
        Algorithm00,
        Variant3,
    )


@register
class Algorithm98(FallbackVariants):
    """Method 01 over positions 3 to 9, then method 32."""

    name = "98"

    class Variant1(Algorithm01):
        # The spec lists the weights 3, 7, 1, 3, 7, 1, 3 for positions 3 to 9 from left
        # to right, so read from the right they cycle as 3, 1, 7.
        positions = Positions(start=3, end=9, check_digit=10)
        weights: ClassVar[list[int]] = [3, 1, 7]

    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Variant1,
        Algorithm32,
    )


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
class AlgorithmA4(SelectedVariant):
    """Two chains of variants, picked by whether positions 3-4 are 99.

    Account codes with 99 at positions 3-4 are checked with method 33, then method 93. All
    others are checked with method 32, then its modulus 7 version, then method 93.
    """

    name = "A4"

    class Chain1(FallbackVariants):
        class Variant2(WeightedMod7):
            positions = Positions(start=4, end=9, check_digit=10)
            weights: ClassVar[list[int]] = [2, 3, 4, 5, 6, 7]

        variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
            Algorithm32,
            Variant2,
            Algorithm93,
        )

    class Chain2(FallbackVariants):
        variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (Algorithm33, Algorithm93)

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm:
        if validate_account_code(account_code)[2:4] == "99":
            return self.Chain2()
        return self.Chain1()


@register
class AlgorithmA5(FallbackVariants):
    """Method 00, then method 10. Account codes starting with 9 must pass method 00."""

    name = "A5"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm00,
        Algorithm10,
    )

    @override
    def allows_fallback(self, account_code: str) -> bool:
        return account_code[0] != "9"


@register
class AlgorithmA6(SelectedVariant):
    """Method 00 for account codes with an 8 at position 2, method 01 for all others."""

    name = "A6"

    @override
    def get_variant(self, account_code: str) -> WeightedModulus:
        if validate_account_code(account_code)[1] == "8":
            return Algorithm00()
        return Algorithm01()


@register
class AlgorithmA7(FallbackVariants):
    name = "A7"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm00,
        Algorithm03,
    )


@register
class AlgorithmA8(SelectedVariant):
    """Method 32, then method 00 over positions 4 to 9.

    Account codes with a 9 at position 3 are checked with the exception of method 51.
    """

    name = "A8"

    class Methods(FallbackVariants):
        class Variant2(Algorithm00):
            positions = Positions(start=4, end=9, check_digit=10)

        variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (Algorithm32, Variant2)

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm:
        if Algorithm51.is_sachkonto(account_code):
            return Algorithm51.Sachkonten()
        return self.Methods()


@register
class AlgorithmB1(FallbackVariants):
    """Method 05, then method 01, then method 00."""

    name = "B1"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm05,
        Algorithm01,
        Algorithm00,
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
class AlgorithmB5(FallbackVariants):
    """Method 05, then method 00. Account codes starting with 8 or 9 must pass method 05."""

    name = "B5"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm05,
        Algorithm00,
    )

    @override
    def allows_fallback(self, account_code: str) -> bool:
        return account_code[0] not in "89"


@register
class AlgorithmB6(SelectedVariant):
    """Method 20 for some account codes, method 53 for all others.

    Method 20 applies to account codes starting with 1 to 9, or with 02691 to 02699. Since
    method 53 needs the bank code, so does this method.
    """

    name = "B6"
    accepts: ClassVar[list[Component]] = [Component.BANK_CODE, Component.ACCOUNT_CODE]

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm:
        validate_account_code(account_code)
        if account_code[0] != "0" or 2691 <= int(account_code[:5]) <= 2699:
            return Algorithm20()
        return Algorithm53()


@register
class AlgorithmB7(SelectedVariant):
    """Method 01 for two ranges of account codes, method 09 for all others.

    The ranges are 0001000000 to 0005999999 and 0700000000 to 0899999999.
    """

    name = "B7"
    ranges: ClassVar[tuple[range, ...]] = (
        range(1_000_000, 6_000_000),
        range(700_000_000, 900_000_000),
    )

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm:
        number = int(validate_account_code(account_code))
        if any(number in accepted for accepted in self.ranges):
            return Algorithm01()
        return Algorithm09()


@register
class AlgorithmB8(FallbackVariants):
    """Method 20, then method 29, then valid for two ranges of account codes.

    The ranges are 5100000000 to 5999999999 and 9010000000 to 9109999999.
    """

    name = "B8"

    class Variant3(AcceptedRanges):
        ranges: ClassVar[tuple[range, ...]] = (
            range(5_100_000_000, 6_000_000_000),
            range(9_010_000_000, 9_110_000_000),
        )

    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm20,
        Algorithm29,
        Variant3,
    )


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

    @staticmethod
    def has_two_leading_zeros(account_code: str) -> bool:
        return account_code.startswith("00") and account_code[2] != "0"

    def compute_eser(self, bank_code: str, account_code: str) -> str:
        """Return the method 52 check digit, or an empty string if there is none."""
        # Bank code XXX5XXXX and account code 00XPXXXXXX give the ESER account number
        # XXXX-XP-XXXXXX, with the leading zeros of the last part dropped.
        return eser_check_digit(bank_code[4:8] + account_code[2], account_code[4:].lstrip("0"))

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
class AlgorithmC2(FallbackVariants):
    """Method 22, then method 00, then method 04."""

    name = "C2"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm22,
        Algorithm00,
        Algorithm04,
    )


@register
class AlgorithmC3(SelectedVariant):
    """Method 58 for account codes starting with 9, method 00 for all others."""

    name = "C3"

    @override
    def get_variant(self, account_code: str) -> WeightedModulus:
        if validate_account_code(account_code)[0] == "9":
            return Algorithm58()
        return Algorithm00()


@register
class AlgorithmC5(SelectedVariant):
    """The length and leading digits of the account code pick the variant.

    - 6-digit account codes with 1 to 8 at position 5, and 9-digit ones with 1 to 8 at
      position 2: method 75.
    - 10-digit account codes starting with 1, 4, 5, 6 or 9: method 29.
    - 10-digit account codes starting with 3: method 00.
    - 8-digit account codes with 3, 4 or 5 at position 3, and 10-digit ones starting with 70
      or 85: method 09.

    All other account codes are invalid.
    """

    name = "C5"

    class Variant4(AcceptedRanges):
        ranges: ClassVar[tuple[range, ...]] = (
            range(30_000_000, 60_000_000),
            range(7_000_000_000, 7_100_000_000),
            range(8_500_000_000, 8_600_000_000),
        )

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm | None:
        number = int(validate_account_code(account_code))
        if 100_000 <= number < 900_000 or 100_000_000 <= number < 900_000_000:
            return Algorithm75()
        if account_code[0] in "14569":
            return Algorithm29()
        if account_code[0] == "3":
            return Algorithm00()
        if self.Variant4.contains(account_code):
            return self.Variant4()
        return None


@register
class AlgorithmC7(FallbackVariants):
    """Method 63, then method 06."""

    name = "C7"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm63,
        Algorithm06,
    )


@register
class AlgorithmC8(FallbackVariants):
    """Method 00, then method 04, then method 07."""

    name = "C8"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm00,
        Algorithm04,
        Algorithm07,
    )


@register
class AlgorithmC9(FallbackVariants):
    """Method 00, then method 07."""

    name = "C9"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm00,
        Algorithm07,
    )


@register
class AlgorithmD0(SelectedVariant):
    """Method 09 for account codes starting with 57, method 20 for all others."""

    name = "D0"

    @override
    def get_variant(self, account_code: str) -> checksum.Algorithm:
        if validate_account_code(account_code).startswith("57"):
            return Algorithm09()
        return Algorithm20()


@register
class AlgorithmD2(FallbackVariants):
    """Method 95, then method 00, then method 68."""

    name = "D2"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm95,
        Algorithm00,
        Algorithm68,
    )


@register
class AlgorithmD6(FallbackVariants):
    """Method 07, then method 03, then method 00."""

    name = "D6"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm07,
        Algorithm03,
        Algorithm00,
    )


@register
class AlgorithmD7(Algorithm00):
    """Method 00, but the check digit is the last digit of the sum instead of its complement."""

    name = "D7"
    minuend = None


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


@register
class AlgorithmE0(Algorithm00):
    """Method 00 with 7 added to the sum."""

    name = "E0"

    @override
    def compute_weighted_sum(self, digits: str) -> int:
        return super().compute_weighted_sum(digits) + 7


@register
class AlgorithmE3(FallbackVariants):
    """Method 00, then method 21."""

    name = "E3"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm00,
        Algorithm21,
    )


@register
class AlgorithmE4(FallbackVariants):
    """Method 02, then method 00."""

    name = "E4"
    variants: ClassVar[tuple[type[checksum.Algorithm], ...]] = (
        Algorithm02,
        Algorithm00,
    )
