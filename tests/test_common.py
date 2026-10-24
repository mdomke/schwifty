"""Tests for the shared helpers in :mod:`schwifty.common`."""

import copy

import pytest

from schwifty import BIC
from schwifty.common import clean


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("DE89 3704", "DE893704"),
        ("a b\tc\nd", "ABCD"),
        ("  x  ", "X"),
        ("", ""),
        ("already", "ALREADY"),
        # Non-breaking spaces count as whitespace, too.
        ("a\u00a0b", "AB"),
        # ``clean`` upper-cases, which expands the German sharp s.
        ("straße", "STRASSE"),
    ],
)
def test_clean(raw: str, expected: str) -> None:
    assert clean(raw) == expected


def test_base_repr() -> None:
    assert repr(BIC("GENODEM1GLS")) == "<BIC=GENODEM1GLS>"


def test_base_equality_and_hash() -> None:
    bic = BIC("GENODEM1GLS")
    assert bic == "GENODEM1GLS"
    assert bic == BIC("GENODEM1GLS")
    assert bic != BIC("MARKDEF1100")
    assert bic != "MARKDEF1100"
    # The hash is the hash of the plain string value.
    assert hash(bic) == hash("GENODEM1GLS")


def test_base_ordering() -> None:
    assert BIC("AAAADE00") < BIC("GENODEM1GLS")
    assert BIC("GENODEM1GLS") > BIC("AAAADE00")
    assert sorted([BIC("MARKDEF1100"), BIC("AAAADE00")]) == [
        BIC("AAAADE00"),
        BIC("MARKDEF1100"),
    ]


def test_base_compact_and_length() -> None:
    bic = BIC("GENODEM1GLS")
    assert bic.compact == "GENODEM1GLS"
    assert bic.length == len(bic) == 11


def test_base_get_slice() -> None:
    bic = BIC("GENODEM1GLS")
    assert bic._get_slice(0, 4) == "GENO"
    assert bic._get_slice(8) == "GLS"
    assert bic._get_slice(0, 11) == "GENODEM1GLS"


def test_base_get_slice_out_of_bounds_returns_empty() -> None:
    bic = BIC("GENODEM1GLS")
    # A start at or beyond the end yields an empty string instead of the
    # truncated slice a plain string would produce.
    assert bic._get_slice(11) == ""
    assert bic._get_slice(20) == ""
    # An end beyond the length also yields an empty string.
    assert bic._get_slice(0, 99) == ""


def test_base_deepcopy() -> None:
    bic = BIC("GENODEM1GLS")
    cloned = copy.deepcopy(bic)
    assert cloned == bic
    assert isinstance(cloned, BIC)
    assert cloned is not bic


def test_base_deepcopy_preserves_invalid_values() -> None:
    # Deep-copying must not re-validate, so an object created with
    # ``allow_invalid=True`` survives the round-trip.
    bic = BIC("GENOXXM1GLS", allow_invalid=True)
    cloned = copy.deepcopy(bic)
    assert str(cloned) == "GENOXXM1GLS"
    assert cloned.is_valid is False
