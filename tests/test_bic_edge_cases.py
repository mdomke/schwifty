"""Edge-case tests for :class:`schwifty.BIC`."""

import pytest

from schwifty import BIC
from schwifty import exceptions


def test_bic_input_is_normalised() -> None:
    # The constructor strips whitespace and upper-cases the value.
    assert BIC("genodem1gls").compact == "GENODEM1GLS"
    assert BIC("GENO DE M1 GLS").compact == "GENODEM1GLS"


@pytest.mark.parametrize("code", ["GENODEM1GL", "GENODEM1GLSX", "GENODEM", ""])
def test_bic_invalid_lengths(code: str) -> None:
    with pytest.raises(exceptions.InvalidLength):
        BIC(code)


def test_bic_swift_compliance_for_eight_character_codes() -> None:
    # Digits in the business party prefix are fine under ISO 9362:2022 but
    # rejected when strict SWIFT compliance is enforced.
    assert BIC("1234DEWW").compact == "1234DEWW"
    with pytest.raises(exceptions.InvalidStructure):
        BIC("1234DEWW", enforce_swift_compliance=True)


def test_bic_candidates_from_bank_code() -> None:
    candidates = BIC.candidates_from_bank_code("FR", "30004")
    assert len(candidates) == 23
    assert all(isinstance(candidate, BIC) for candidate in candidates)
    # Candidates are sorted with the registry's primary records first.
    assert candidates[0] == "BNPAFRPPIFN"


def test_bic_from_bank_code_prefers_the_generic_code() -> None:
    # Among the many BNP Paribas candidates the generic code without a
    # branch code wins.
    assert BIC.from_bank_code("FR", "30004") == "BNPAFRPP"


def test_bic_type_and_formatted_for_eight_character_code() -> None:
    bic = BIC("GENODEM0")
    assert bic.type == "testing"
    assert bic.branch_code == ""
    assert bic.formatted == "GENO DE M0"
