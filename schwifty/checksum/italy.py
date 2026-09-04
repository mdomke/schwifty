from __future__ import annotations

import string

from schwifty import checksum
from schwifty._compat import override


_CHAR_MAP: dict[str, int] = {
    **{str(i): i for i in range(10)},
    **{c: i for i, c in enumerate(string.ascii_uppercase)},
    **{c: i for i, c in enumerate(string.ascii_lowercase)},
}

_ODDS: tuple[int, ...] = (
    1,
    0,
    5,
    7,
    9,
    13,
    15,
    17,
    19,
    21,
    2,
    4,
    18,
    20,
    11,
    3,
    6,
    8,
    12,
    14,
    16,
    10,
    22,
    25,
    24,
    23,
)


def get_index(char: str) -> int:
    return _CHAR_MAP[char]


@checksum.register("IT", "SM")
class DefaultAlgorithm(checksum.Algorithm):
    name = "default"

    @override
    def compute(self, components: list[str]) -> str:
        value = "".join(components)
        sum_ = 0
        for i, char in enumerate(value):
            if (i + 1) % 2 == 0:
                sum_ += get_index(char)
            else:
                sum_ += _ODDS[get_index(char)]
        return string.ascii_uppercase[sum_ % 26]
