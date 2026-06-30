import pytest

from schwifty.bban import BBAN
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
