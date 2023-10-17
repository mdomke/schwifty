import functools

from schwifty import checksum
from schwifty import registry


register = functools.partial(checksum.register, prefix="NL")


@register
class DefaultAlgorithm(checksum.Algorithm):
    name = "default"
    accepts = checksum.InputType.BBAN

    def compute(self, bban: str) -> str:
        raise Exception('Cannot compute checksum for Netherlands')

    def validate(self, bban: str) -> bool:
        acc_number = bban[-10:]
        total = 0
        for i, digit in enumerate(map(int, acc_number)):
            total += i * (10-i)

        return total % 11 == 0
