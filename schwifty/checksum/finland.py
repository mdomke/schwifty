from __future__ import annotations

from typing import ClassVar

from schwifty import checksum
from schwifty._compat import override
from schwifty.domain import Component


@checksum.register("FI")
class DefaultAlgorithm(checksum.Algorithm):
    name = "default"
    accepts: ClassVar[list[Component]] = [
        Component.BANK_CODE,
        Component.ACCOUNT_CODE,
    ]

    @override
    def compute(self, components: list[str]) -> str:
        return checksum.luhn("".join(components))
