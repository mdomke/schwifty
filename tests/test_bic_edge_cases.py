"""Edge-case tests for :class:`schwifty.BIC`."""

import re

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
    # BNPAFRPP and the equivalent BNPAFRPPXXX are listed once.
    assert len(candidates) == 22
    assert "BNPAFRPPXXX" not in candidates
    assert all(isinstance(candidate, BIC) for candidate in candidates)
    # Candidates are sorted by rank, so the first one is the BIC that ``from_bank_code`` picks.
    assert candidates[0] == "BNPAFRPP"
    assert candidates[0] == BIC.from_bank_code("FR", "30004")


def test_bic_from_bank_code_prefers_the_generic_code() -> None:
    # Among the many BNP Paribas candidates the generic code without a
    # branch code wins.
    assert BIC.from_bank_code("FR", "30004") == "BNPAFRPP"


def test_bic_type_and_formatted_for_eight_character_code() -> None:
    bic = BIC("GENODEM0")
    assert bic.type == "testing"
    assert bic.branch_code == ""
    assert bic.formatted == "GENO DE M0"


def test_bic_json_schema_pattern_is_anchored() -> None:
    # JSON Schema treats "pattern" as a search, while BIC validation uses fullmatch.
    # An unanchored pattern therefore accepts strings that merely contain a valid BIC.
    from pydantic import BaseModel

    from schwifty import bic as bic_module

    class Model(BaseModel):
        bic: BIC

    pattern = Model.model_json_schema()["properties"]["bic"]["pattern"]
    assert pattern.startswith("^")
    assert pattern.endswith("$")
    assert bic_module._bic_iso9362_re.pattern == pattern
    assert bic_module._bic_swift_re.pattern.startswith("^")
    assert bic_module._bic_swift_re.pattern.endswith("$")

    # Reproduce jsonschema's search semantics against the published pattern.
    compiled = re.compile(pattern)
    for invalid in ("XGENODEM1", "GENODEM1X", "AAGENODEM1"):
        assert compiled.search(invalid) is None
        assert compiled.fullmatch(invalid) is None
    assert compiled.search("GENODEM1GLS") is not None
    assert compiled.fullmatch("GENODEM1GLS") is not None
