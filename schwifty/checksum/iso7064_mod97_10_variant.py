from schwifty import checksum
from schwifty._compat import override


# Mauretania (MR)
# Tunesia (TN)
@checksum.register("MR", "TN")
class DefaultAlgorithm(checksum.ISO7064_mod97_10):
    name = "default"

    @override
    def post_process(self, r: int) -> int:
        return 97 - r
