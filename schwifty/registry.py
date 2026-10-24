from __future__ import annotations

import itertools
import json
import re
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field
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


def add_bban_regex(spec: dict[str, Any]) -> dict[str, Any]:
    if "regex" not in spec:
        spec["regex"] = re.compile(convert_bban_spec_to_regex(spec["bban_spec"]))
    return spec


def merge_dicts(left: dict[Key, Any], right: dict[Key, Any]) -> dict[Key, Any]:
    merged = {}
    for key in left.keys() & right:
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


def _registry_directory(name: str) -> Path:
    package = __package__ or "schwifty"
    directory = files(package) / f"{name}_registry"
    assert isinstance(directory, Path)
    return directory


@dataclass(slots=True)
class CountryBanks:
    banks: list[Bank] = field(default_factory=list)
    by_bank_code: defaultdict[str, list[Bank]] = field(default_factory=lambda: defaultdict(list))
    by_bic: defaultdict[str, list[Bank]] = field(default_factory=lambda: defaultdict(list))


class Registry:
    def __init__(self) -> None:
        self._registry: dict[Key, Value] = {}
        self._banks: dict[str, CountryBanks] = {}
        self._bank_file_index: dict[str, list[Path]] | None = None

    def _has(self, name: Key) -> bool:
        return name in self._registry

    def _save(self, name: Key, data: Value) -> Value:
        self._registry[name] = data
        return data

    def _get(self, name: Key) -> Value:
        if self._has(name):
            return self._registry[name]

        data: Value | None = None
        assert isinstance(name, str)
        for entry in sorted(_registry_directory(name).glob("*.json")):
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
                data[country] = add_bban_regex(spec)

        return self._save(name, data)

    def get_iban_spec(self, country_code: str) -> IBANSpec:
        spec = self._get("iban")
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
            aspirational=data.get("aspirational", False),
        )

    def _parse_bank(self, data: dict[str, Any] | Bank) -> Bank:
        if isinstance(data, Bank):
            return data
        return Bank(
            country_code=data["country_code"],
            bic=data["bic"],
            bank_code=data["bank_code"],
            name=data["name"],
            short_name=data.get("short_name"),
            primary=data.get("primary", False),
            checksum_algo=data.get("checksum_algo", "default"),
        )

    def get_banks_by_country(self, country_code: str) -> list[Bank]:
        return self._get_country_banks(country_code).banks

    def get_banks_by_code(self, country_code: str, bank_code: str) -> list[Bank]:
        return self._get_country_banks(country_code).by_bank_code.get(bank_code, [])

    def get_banks_by_bic(self, bic: str) -> list[Bank]:
        # Only the registry of the BIC's own country is searched, so that a lookup doesn't
        # require loading the banks of all countries.
        return self._get_country_banks(bic[4:6].upper()).by_bic.get(bic, [])

    def get_countries(self) -> list[str]:
        return list(self._bank_files())

    def get_all_banks(self) -> list[Bank]:
        return [
            bank
            for country_code in self.get_countries()
            for bank in self.get_banks_by_country(country_code)
        ]

    def _bank_files(self) -> dict[str, list[Path]]:
        if self._bank_file_index is None:
            index: dict[str, list[Path]] = defaultdict(list)
            for path in sorted(_registry_directory("bank").glob("*.json")):
                # File names follow the pattern <source>_<country>[.v2].json
                country_code = path.name.split(".")[0].rsplit("_", 1)[-1].upper()
                index[country_code].append(path)
            self._bank_file_index = dict(index)
        return self._bank_file_index

    def _get_country_banks(self, country_code: str) -> CountryBanks:
        if (banks := self._banks.get(country_code)) is not None:
            return banks

        entries: list[dict[str, Any]] = []
        for path in self._bank_files().get(country_code, []):
            with path.open(encoding="utf-8") as fp:
                chunk = json.load(fp)
            entries.extend(parse_v2(chunk) if path.stem.endswith("v2") else chunk)

        # The indexes share the same Bank instances to keep the memory footprint low.
        banks = CountryBanks()
        for entry in entries:
            bank = self._parse_bank(entry)
            banks.banks.append(bank)
            if bank.bank_code:
                banks.by_bank_code[bank.bank_code].append(bank)
            if bank.bic:
                banks.by_bic[bank.bic].append(bank)
        self._banks[country_code] = banks
        return banks


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


def get_all_banks() -> list[Bank]:
    return _default_registry.get_all_banks()
