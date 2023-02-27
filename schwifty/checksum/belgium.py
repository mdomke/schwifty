import functools

from schwifty import checksum
from schwifty import registry


register = functools.partial(checksum.register, prefix="BE")


@register
class DefaultAlgorithm(checksum.Algorithm):
    name = "default"
    accepts = checksum.InputType.BBAN
    checksum_length = 2

    def compute(self, bban: str) -> str:
        spec = registry.get("iban")
        assert isinstance(spec, dict)
        checksum = int(bban[: spec["BE"]["bban_length"] - self.checksum_length]) % 97
        # Specific value in case checksum is expliclity 97
        checksum = checksum if checksum != 0 else 97
        return str(checksum).zfill(self.checksum_length)

    def validate(self, bban: str) -> bool:
        return bban[-self.checksum_length :] == self.compute(bban[: -self.checksum_length])
