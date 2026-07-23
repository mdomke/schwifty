from __future__ import annotations

import string
from typing import ClassVar

from schwifty import checksum
from schwifty._compat import override
from schwifty.domain import Component


CHECK_DIGIT_INDEX = 8


@checksum.register("IS")
class DefaultAlgorithm(checksum.Algorithm):
    name = "default"
    accepts: ClassVar[list[Component]] = [
        Component.ACCOUNT_HOLDER_ID,
    ]

    @override
    def compute(self, components: list[str]) -> str:
        [account_holder_id] = components
        weights = [3, 2, 7, 6, 5, 4, 3, 2]
        remainder = checksum.weighted(account_holder_id, 11, weights)
        return str(remainder) if remainder == 0 else str(11 - remainder)

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        [account_holder_id] = components
        return self.compute(components) == account_holder_id[CHECK_DIGIT_INDEX]

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        # The check digit sits at a fixed position in the account holder id and does
        # not feed back into its own computation, so trying every value there yields
        # the single valid one -- or none when the id requires a check digit of 10.
        [account_holder_id] = components
        for digit in string.digits:
            candidate = (
                account_holder_id[:CHECK_DIGIT_INDEX]
                + digit
                + account_holder_id[CHECK_DIGIT_INDEX + 1 :]
            )
            if self.validate([candidate], ""):
                return [candidate]
        return None
