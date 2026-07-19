import copy
import pickle

import pytest

from schwifty.bban import BBAN
from schwifty.exceptions import GenerateRandomOverflowError
from schwifty.exceptions import InvalidBBANChecksum


def test_validate_national_checksum() -> None:
    # A valid national checksum returns True (consistent with the "no checksum
    # algorithm" case), while an invalid one raises InvalidBBANChecksum.
    assert BBAN("BE", "539007547034").validate_national_checksum() is True
    assert BBAN("GB", "WEST12345698765432").validate_national_checksum() is True
    with pytest.raises(InvalidBBANChecksum):
        BBAN("BE", "539007547035").validate_national_checksum()

    # Bosnia and Herzegovina (BA) uses ISO 7064 mod 97-10; it was previously
    # registered under the wrong country code "BT" (#264), so the national
    # checksum was never validated.
    assert BBAN("BA", "1290079401028494").validate_national_checksum() is True
    with pytest.raises(InvalidBBANChecksum):
        BBAN("BA", "1290079401028400").validate_national_checksum()


@pytest.mark.parametrize("country_code", ["DE", "ES", "GB", "FR", "PL"])
def test_random(country_code: str) -> None:
    n = 100
    bbans = {BBAN.random(country_code) for _ in range(n)}
    assert len(bbans) == n

    for bban in bbans:
        assert bban.bank is not None
        assert bban.country_code == country_code

    assert any(
        bban.bank is None
        for bban in (BBAN.random(country_code, use_registry=False) for _ in range(n))
    )


def test_random_national_checksum_overflow(monkeypatch: pytest.MonkeyPatch) -> None:
    # When no generated candidate ever satisfies the national checksum, random()
    # exhausts its retries and raises GenerateRandomOverflowError rather than
    # returning a BBAN with an invalid checksum.
    def always_invalid(self: BBAN) -> bool:
        raise InvalidBBANChecksum

    monkeypatch.setattr(BBAN, "validate_national_checksum", always_invalid)
    with pytest.raises(GenerateRandomOverflowError):
        BBAN.random("DE")


def test_pickle_roundtrip() -> None:
    bban = BBAN("CH", "04835012345678009")
    for proto in range(pickle.HIGHEST_PROTOCOL + 1):
        restored = pickle.loads(pickle.dumps(bban, protocol=proto))
        assert restored == bban
        assert restored.country_code == bban.country_code


def test_deepcopy() -> None:
    bban = BBAN("CH", "04835012345678009")
    bban_copy = copy.deepcopy(bban)
    assert bban_copy == bban
    assert bban_copy.country_code == bban.country_code
    assert id(bban_copy) != id(bban)
