from __future__ import annotations

import itertools
import json
import re
from collections import defaultdict
from contextlib import suppress
from pathlib import Path
from typing import Any


try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files  # type: ignore

from schwifty import exceptions
from schwifty.domain import Bank
from schwifty.domain import Component
from schwifty.domain import IBANSpec
from schwifty.domain import Range


Key = str | tuple[str, ...]
Value = dict[Key, Any] | list[dict[Key, Any]]


_spec_to_re: dict[str, str] = {"n": r"\d", "a": r"[A-Z]", "c": r"[A-Za-z0-9]", "e": r" "}


def convert_bban_spec_to_regex(spec: str) -> str:
    spec_re = rf"(\d+)(!)?([{''.join(_spec_to_re.keys())}])"

    def convert(match: re.Match[str]) -> str:
        quantifier = ("{{{}}}" if match.group(2) else "{{1,{}}}").format(match.group(1))
        return _spec_to_re[match.group(3)] + quantifier

    return rf"^{re.sub(spec_re, convert, spec)}$"


def add_bban_regex(country: str, spec: dict[str, Any]) -> dict[str, Any]:
    if "regex" not in spec:
        spec["regex"] = re.compile(convert_bban_spec_to_regex(spec["bban_spec"]))
    return spec


def merge_dicts(left: dict[Key, Any], right: dict[Key, Any]) -> dict[Key, Any]:
    merged = {}
    for key in frozenset(right) & frozenset(left):
        left_value, right_value = left[key], right[key]
        if isinstance(left_value, dict) and isinstance(right_value, dict):
            merged[key] = merge_dicts(left_value, right_value)
        else:
            merged[key] = right_value

    for key, value in itertools.chain(left.items(), right.items()):
        if key not in merged:
            merged[key] = value
    return merged


def parse_v2(data: dict[str, Any]) -> list[dict[str, Any]]:
    entries = data["entries"]

    def expand(entry: dict[str, Any], src: str, dst: str) -> list[dict[str, Any]]:
        values = entry.pop(src)
        entry.setdefault("primary", False)
        return [{**entry, dst: value} for value in values]

    return list(
        itertools.chain.from_iterable(
            expand(entry, src=data["expand_from"], dst=data["expand_into"]) for entry in entries
        )
    )


class Registry:
    def __init__(self) -> None:
        self._registry: dict[Key, Value] = {}

    def has(self, name: Key) -> bool:
        return name in self._registry

    def save(self, name: Key, data: Value) -> Value:
        self._registry[name] = data
        return data

    def get(self, name: Key) -> Value:
        if self.has(name):
            return self._registry[name]

        if name == "country":
            self._build_country_index()
            return self._registry["country"]
        if name == "bank_code":
            self._build_bank_code_index()
            return self._registry["bank_code"]
        if name == "bic":
            self._build_bic_index()
            return self._registry["bic"]

        data: Value | None = None
        package = __package__ or "schwifty"
        directory = files(package) / f"{name}_registry"
        assert isinstance(directory, Path)
        for entry in sorted(directory.glob("*.json")):
            assert isinstance(entry, Path)
            with entry.open(encoding="utf-8") as fp:
                chunk = json.load(fp)
                if entry.stem.endswith("v2"):
                    chunk = parse_v2(chunk)
                if data is None:
                    data = chunk
                elif isinstance(data, list):
                    data.extend(chunk)
                elif isinstance(data, dict):
                    data = merge_dicts(data, chunk)
        if data is None:
            raise ValueError(f"Failed to load registry {name}")

        # Automatically apply BBAN regex conversion when loading "iban"
        if name == "iban":
            assert isinstance(data, dict)
            for country, spec in data.items():
                assert isinstance(country, str)
                data[country] = add_bban_regex(country, spec)

        return self.save(name, data)

    def get_iban_spec(self, country_code: str) -> IBANSpec:
        spec = self.get("iban")
        assert isinstance(spec, dict)
        try:
            raw_spec = spec[country_code]
        except KeyError as e:
            raise exceptions.InvalidCountryCode(f"Unknown country-code '{country_code}'") from e

        if isinstance(raw_spec, IBANSpec):
            return raw_spec
        parsed = self._parse_iban_spec(country_code, raw_spec)
        spec[country_code] = parsed
        return parsed

    def _parse_iban_spec(self, country_code: str, data: dict[str, Any]) -> IBANSpec:
        raw_positions = data.get("positions", {})
        positions = {}
        for comp in Component:
            coords = raw_positions.get(comp.value) or raw_positions.get(comp)
            if coords:
                positions[comp] = Range(coords[0], coords[1])
            else:
                positions[comp] = Range(0, 0)

        raw_bic_lookup = data.get("bic_lookup_components") or ["bank_code"]
        bic_lookup_components = []
        for x in raw_bic_lookup:
            with suppress(ValueError):
                bic_lookup_components.append(Component(x))

        defaults = {
            k: str(v) for k, v in data.items() if k.startswith("default_") and v is not None
        }

        regex = data.get("regex")
        if not isinstance(regex, re.Pattern):
            regex = re.compile(convert_bban_spec_to_regex(data["bban_spec"]))

        return IBANSpec(
            country=country_code,
            bban_spec=data["bban_spec"],
            bban_length=data["bban_length"],
            iban_spec=data["iban_spec"],
            iban_length=data["iban_length"],
            in_sepa_zone=data.get("in_sepa_zone", False),
            regex=regex,
            positions=positions,
            bic_lookup_components=bic_lookup_components,
            defaults=defaults,
        )

    def _parse_bank(self, data: dict[Key, Any]) -> Bank:
        if isinstance(data, Bank):
            return data
        return Bank(
            country_code=data["country_code"],
            bic=data["bic"],
            bank_code=data["bank_code"],
            name=data["name"],
            short_name=data.get("short_name"),
            primary=data.get("primary", False),
        )

    def get_banks_by_country(self, country_code: str) -> list[Bank]:
        if not self.has("country"):
            self._build_country_index()
        country_index = self.get("country")
        assert isinstance(country_index, dict)
        return country_index.get(country_code, [])

    def get_banks_by_code(self, country_code: str, bank_code: str) -> list[Bank]:
        if not self.has("bank_code"):
            self._build_bank_code_index()
        bank_code_index = self.get("bank_code")
        assert isinstance(bank_code_index, dict)
        return bank_code_index.get((country_code, bank_code), [])

    def get_banks_by_bic(self, bic: str) -> list[Bank]:
        if not self.has("bic"):
            self._build_bic_index()
        bic_index = self.get("bic")
        assert isinstance(bic_index, dict)
        return bic_index.get(bic, [])

    def get_countries(self) -> list[str]:
        if not self.has("country"):
            self._build_country_index()
        country_index = self.get("country")
        assert isinstance(country_index, dict)
        return [str(k) for k in country_index]

    def _build_country_index(self) -> None:
        base = self.get("bank")
        assert isinstance(base, list)
        data = defaultdict(list)
        for entry in base:
            assert isinstance(entry, dict)
            country_code = entry.get("country_code")
            if country_code:
                data[country_code].append(self._parse_bank(entry))
        self.save("country", dict(data))

    def _build_bank_code_index(self) -> None:
        base = self.get("bank")
        assert isinstance(base, list)
        data = defaultdict(list)
        for entry in base:
            assert isinstance(entry, dict)
            country_code = entry.get("country_code")
            bank_code = entry.get("bank_code")
            if country_code and bank_code:
                data[(country_code, bank_code)].append(self._parse_bank(entry))
        self.save("bank_code", dict(data))

    def _build_bic_index(self) -> None:
        base = self.get("bank")
        assert isinstance(base, list)
        data = defaultdict(list)
        for entry in base:
            assert isinstance(entry, dict)
            bic = entry.get("bic")
            if bic:
                data[bic].append(self._parse_bank(entry))
        self.save("bic", dict(data))


_default_registry = Registry()


def get_iban_spec(country_code: str) -> IBANSpec:
    return _default_registry.get_iban_spec(country_code)


def get_banks_by_country(country_code: str) -> list[Bank]:
    return _default_registry.get_banks_by_country(country_code)


def get_banks_by_code(country_code: str, bank_code: str) -> list[Bank]:
    return _default_registry.get_banks_by_code(country_code, bank_code)


def get_banks_by_bic(bic: str) -> list[Bank]:
    return _default_registry.get_banks_by_bic(bic)


def get_countries() -> list[str]:
    return _default_registry.get_countries()


# Raw/legacy helpers for test backward compatibility
def get(name: Key) -> Value:
    return _default_registry.get(name)


def has(name: Key) -> bool:
    return _default_registry.has(name)


def save(name: Key, data: Value) -> Value:
    return _default_registry.save(name, data)
