from __future__ import annotations

import string
from typing import ClassVar

from schwifty import checksum
from schwifty._compat import override
from schwifty.domain import Component


@checksum.register("CZ", "SK")
class DefaultAlgorithm(checksum.Algorithm):
    name = "default"
    weights: ClassVar[list[int]] = [6, 3, 7, 9, 10, 5, 8, 4, 2, 1]
    accepts: ClassVar[list[Component]] = [
        Component.BRANCH_CODE,
        Component.ACCOUNT_CODE,
    ]

    @override
    def compute(self, components: list[str]) -> str:
        return ""

    @override
    def validate(self, components: list[str], expected: str) -> bool:
        branch_code, account_code = components

        d1 = checksum.weighted(branch_code, 11, self.weights[4:])
        d2 = checksum.weighted(account_code, 11, self.weights)
        return d1 == 0 and d2 == 0

    @override
    def solve(self, components: list[str]) -> list[str] | None:
        # There is no dedicated check digit: the whole branch and account codes must
        # each weigh to 0 mod 11. Their trailing position has weight 1, so cycling it
        # reaches every residue but one -- the value 10, which no single digit can
        # supply and which then triggers a regeneration.
        branch_code, account_code = components
        branch = self._solve_code(branch_code, self.weights[4:])
        account = self._solve_code(account_code, self.weights)
        if branch is None or account is None:
            return None
        return [branch, account]

    @staticmethod
    def _solve_code(code: str, weights: list[int]) -> str | None:
        for digit in string.digits:
            candidate = code[:-1] + digit
            if checksum.weighted(candidate, 11, weights) == 0:
                return candidate
        return None
