"""Regression tests for code normalization in the public generation and lookup APIs."""

from random import Random

import pytest

from schwifty import BIC
from schwifty import IBAN
from schwifty import registry


@pytest.mark.parametrize(
    ("canonical", "variant"),
    [
        (("DE", "37040044", "532013000"), ("de", "37040044", "532013000")),
        (("DE", "37040044", "532013000"), (" d e ", " 3704 0044 ", " 532013000 ")),
        (("GB", "NWBK", "31926819"), ("gb", "nwbk", "31926819")),
        (("GB", "NWBK", "31926819", "601613"), (" gB ", " n w b k ", "31926819", "601613")),
    ],
)
def test_generate_normalizes_codes(canonical: tuple[str, ...], variant: tuple[str, ...]) -> None:
    assert IBAN.generate(*variant).compact == IBAN.generate(*canonical).compact


@pytest.mark.parametrize("country_code", ["DE", "de", " d e ", " dE "])
def test_random_normalizes_country_code(country_code: str) -> None:
    expected = IBAN.random(country_code="DE", random=Random(7))  # noqa: S311
    assert IBAN.random(country_code=country_code, random=Random(7)) == expected  # noqa: S311


@pytest.mark.parametrize(
    ("canonical", "variant"),
    [
        (("DE", "43060967"), ("de", "43060967")),
        (("DE", "43060967"), (" dE ", " 4306 0967 ")),
        (("GB", "NWBK"), ("GB", "nwbk")),
        (("GB", "NWBK"), ("gb", " n w b k ")),
    ],
)
def test_bic_from_bank_code_normalizes_codes(
    canonical: tuple[str, str], variant: tuple[str, str]
) -> None:
    assert BIC.from_bank_code(*variant).compact == BIC.from_bank_code(*canonical).compact


@pytest.mark.parametrize(
    ("canonical", "variant"),
    [
        (("DE", "43060967"), ("de", "43060967")),
        (("DE", "43060967"), (" dE ", " 4306 0967 ")),
    ],
)
def test_candidates_from_bank_code_normalizes_codes(
    canonical: tuple[str, str], variant: tuple[str, str]
) -> None:
    assert BIC.candidates_from_bank_code(*variant) == BIC.candidates_from_bank_code(*canonical)


@pytest.mark.parametrize(
    ("canonical", "variant"),
    [
        (("GB", "NWBK"), ("gb", "nwbk")),
        (("GB", "NWBK"), (" gB ", " n w b k ")),
        (("DE", "10000000"), ("de", " 1000 0000 ")),
    ],
)
def test_get_banks_by_code_normalizes_codes(
    canonical: tuple[str, str], variant: tuple[str, str]
) -> None:
    expected = registry.get_banks_by_code(*canonical)
    assert expected
    assert registry.get_banks_by_code(*variant) == expected


@pytest.mark.parametrize("country_code", ["DE", "de", " d e "])
def test_get_banks_by_country_normalizes_codes(country_code: str) -> None:
    assert registry.get_banks_by_country(country_code) == registry.get_banks_by_country("DE")
