import string
from functools import partial

from schwifty import checksum
from schwifty import registry


register = partial(checksum.register, prefix="IT")


def get_index(char: str) -> int:
    try:
        return string.digits.index(char)
    except ValueError:
        return string.ascii_uppercase.index(char.upper())


@register
class DefaultAlgorithm(checksum.Algorithm):
    name = "default"
    accepts = checksum.InputType.BBAN
    checksum_length = 1

    def compute(self, bban: str) -> str:
        spec = registry.get("iban")
        assert isinstance(spec, dict)

        odds = (
            [1, 0, 5, 7, 9, 13, 15]
            + [17, 19, 21, 2, 4, 18, 20]
            + [11, 3, 6, 8, 12, 14, 16]
            + [10, 22, 25, 24, 23]
        )
        sum_ = 0
        for i, char in enumerate(bban[self.checksum_length - spec["IT"]["bban_length"] :]):
            if (i + 1) % 2 == 0:
                sum_ += get_index(char)
            else:
                sum_ += odds[get_index(char)]
        return string.ascii_uppercase[sum_ % 26]

    def validate(self, bban: str) -> bool:
        return bban[0] == self.compute(bban[self.checksum_length :])
