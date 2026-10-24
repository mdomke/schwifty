"""Tests for the registry loading helpers and domain value objects."""

import re
from typing import Any

import pytest

from schwifty import exceptions
from schwifty import registry
from schwifty.domain import Bank
from schwifty.domain import Component
from schwifty.domain import IBANSpec
from schwifty.domain import Range
from schwifty.registry import add_bban_regex
from schwifty.registry import convert_bban_spec_to_regex
from schwifty.registry import merge_dicts
from schwifty.registry import parse_v2


@pytest.mark.parametrize(
    ("spec", "pattern"),
    [
        ("8!n", r"^\d{8}$"),
        ("4!a2!n", r"^[A-Z]{4}\d{2}$"),
        ("3!c", r"^[A-Za-z0-9]{3}$"),
        ("2!e", r"^ {2}$"),
        ("5n", r"^\d{1,5}$"),
        ("4!a10!c2!n", r"^[A-Z]{4}[A-Za-z0-9]{10}\d{2}$"),
        ("1!n1!a", r"^\d{1}[A-Z]{1}$"),
    ],
)
def test_convert_bban_spec_to_regex(spec: str, pattern: str) -> None:
    assert convert_bban_spec_to_regex(spec) == pattern


def test_bban_spec_regex_exact_length() -> None:
    regex = re.compile(convert_bban_spec_to_regex("8!n"))
    assert regex.match("12345678")
    assert not regex.match("1234567")
    assert not regex.match("123456789")


def test_bban_spec_regex_variable_length() -> None:
    # Without the ``!`` marker the count is an upper bound, not exact.
    regex = re.compile(convert_bban_spec_to_regex("5n"))
    for length in range(1, 6):
        assert regex.match("1" * length)
    assert not regex.match("1" * 6)


def test_bban_spec_regex_character_classes() -> None:
    assert re.compile(convert_bban_spec_to_regex("3!c")).match("A1b")
    assert not re.compile(convert_bban_spec_to_regex("3!c")).match("A!b")
    # The ``e`` class matches spaces only.
    assert re.compile(convert_bban_spec_to_regex("2!e")).match("  ")
    assert not re.compile(convert_bban_spec_to_regex("2!e")).match("AB")


def test_merge_dicts_disjoint_and_overlapping_keys() -> None:
    assert merge_dicts({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
    assert merge_dicts({"a": 1}, {"a": 2}) == {"a": 2}
    assert merge_dicts({}, {"a": 1}) == {"a": 1}
    assert merge_dicts({"a": 1}, {}) == {"a": 1}


def test_merge_dicts_merges_nested_dicts() -> None:
    left: dict[registry.Key, Any] = {"x": {"p": 1, "q": 2}}
    right: dict[registry.Key, Any] = {"x": {"q": 3, "r": 4}}
    assert merge_dicts(left, right) == {"x": {"p": 1, "q": 3, "r": 4}}


def test_merge_dicts_non_dict_overrides_dict() -> None:
    assert merge_dicts({"x": {"p": 1}}, {"x": 5}) == {"x": 5}


def test_merge_dicts_does_not_mutate_inputs() -> None:
    left: dict[registry.Key, Any] = {"a": {"n": 1}}
    merged = merge_dicts(left, {"a": {"m": 2}})
    assert left == {"a": {"n": 1}}
    assert merged == {"a": {"n": 1, "m": 2}}


def test_parse_v2_expands_entries() -> None:
    data = {
        "expand_from": "bank_codes",
        "expand_into": "bank_code",
        "entries": [
            {"name": "Bank A", "bic": "AAAAAAAA", "bank_codes": ["111", "222"]},
            {"name": "Bank B", "bic": "BBBBBBBB", "bank_codes": ["333"], "primary": True},
        ],
    }
    assert parse_v2(data) == [
        {"name": "Bank A", "bic": "AAAAAAAA", "primary": False, "bank_code": "111"},
        {"name": "Bank A", "bic": "AAAAAAAA", "primary": False, "bank_code": "222"},
        {"name": "Bank B", "bic": "BBBBBBBB", "primary": True, "bank_code": "333"},
    ]


def test_add_bban_regex() -> None:
    spec = add_bban_regex({"bban_spec": "8!n"})
    assert isinstance(spec["regex"], re.Pattern)
    assert spec["regex"].pattern == r"^\d{8}$"


def test_add_bban_regex_keeps_existing() -> None:
    existing = re.compile("custom")
    spec = add_bban_regex({"bban_spec": "8!n", "regex": existing})
    assert spec["regex"] is existing


def test_get_iban_spec_unknown_country() -> None:
    with pytest.raises(exceptions.InvalidCountryCode, match="Unknown country-code 'XX'"):
        registry.get_iban_spec("XX")


def test_get_iban_spec_is_cached() -> None:
    assert registry.get_iban_spec("DE") is registry.get_iban_spec("DE")


def test_get_iban_spec_fields() -> None:
    spec = registry.get_iban_spec("DE")
    assert spec.country == "DE"
    assert spec.bban_spec == "8!n10!n"
    assert spec.bban_length == 18
    assert spec.iban_length == 22
    assert spec.in_sepa_zone is True
    assert spec.positions[Component.BANK_CODE] == Range(0, 8)
    assert spec.positions[Component.ACCOUNT_CODE] == Range(8, 18)


def test_lookups_for_unknown_keys_return_empty() -> None:
    assert registry.get_banks_by_code("DE", "00000000") == []
    assert registry.get_banks_by_bic("DEUTDEDB999") == []
    assert registry.get_banks_by_country("XX") == []


def test_range() -> None:
    range_ = Range(2, 5)
    assert range_.length == 3
    assert range_.is_empty is False
    assert range_.cut("abcdefgh") == "cde"


def test_range_empty() -> None:
    assert Range() == Range(0, 0)
    assert Range().is_empty is True
    assert Range().length == 0
    # A range starting at 0 is not empty when it has a positive length.
    assert Range(0, 3).is_empty is False
    assert Range(0, 3).cut("abcdef") == "abc"


def test_iban_spec_has_positions() -> None:
    spec = IBANSpec(
        country="ZZ",
        bban_spec="",
        bban_length=0,
        iban_spec="",
        iban_length=0,
        in_sepa_zone=False,
        regex=re.compile("$"),
        positions={},
    )
    assert spec.has_positions is False
    assert registry.get_iban_spec("DE").has_positions is True
    # Honduras defines a BBAN regex but no component positions.
    assert registry.get_iban_spec("HN").has_positions is False


def test_bank_defaults() -> None:
    bank = Bank(country_code="DE", bic="TESTDEFF", bank_code="12345678", name="Test Bank")
    assert bank.short_name is None
    assert bank.primary is False
    assert bank.checksum_algo == "default"


def test_bank_dict_style_access_is_deprecated() -> None:
    bank = Bank(country_code="DE", bic="TESTDEFF", bank_code="12345678", name="Test Bank")
    with pytest.deprecated_call():
        assert bank["name"] == "Test Bank"
    with pytest.deprecated_call():
        assert bank.get("bank_code") == "12345678"


def test_bank_dict_style_get_with_default() -> None:
    bank = Bank(country_code="DE", bic="TESTDEFF", bank_code="12345678", name="Test Bank")
    with pytest.deprecated_call():
        assert bank.get("nonexistent") is None
    with pytest.deprecated_call():
        assert bank.get("nonexistent", "fallback") == "fallback"


def test_bank_dict_style_missing_key() -> None:
    bank = Bank(country_code="DE", bic="TESTDEFF", bank_code="12345678", name="Test Bank")
    with pytest.deprecated_call(), pytest.raises(KeyError):
        bank["nonexistent"]
