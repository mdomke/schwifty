from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from dataclasses import field
from typing import Any


class DictCompatMixin:
    def __getitem__(self, key: Any) -> Any:
        if hasattr(key, "value"):
            key = key.value
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None

    def get(self, key: Any, default: Any = None) -> Any:
        if hasattr(key, "value"):
            key = key.value
        return getattr(self, key, default)


class Component(enum.StrEnum):
    ACCOUNT_ID = enum.auto()
    ACCOUNT_TYPE = enum.auto()
    ACCOUNT_CODE = enum.auto()
    ACCOUNT_HOLDER_ID = enum.auto()
    CURRENCY_CODE = enum.auto()
    BANK_CODE = enum.auto()
    BRANCH_CODE = enum.auto()
    NATIONAL_CHECKSUM_DIGITS = enum.auto()


@dataclass
class Range:
    start: int = 0
    end: int = 0

    @property
    def length(self) -> int:
        return self.end - self.start

    @property
    def is_empty(self) -> bool:
        return self.start == 0 and self.end == 0

    def cut(self, s: str) -> str:
        return s[self.start : self.end]


@dataclass
class IBANSpec(DictCompatMixin):
    country: str
    bban_spec: str
    bban_length: int
    iban_spec: str
    iban_length: int
    in_sepa_zone: bool
    regex: re.Pattern[str]
    positions: dict[Component, Range] = field(default_factory=dict)
    bic_lookup_components: list[Component] = field(default_factory=list)
    defaults: dict[str, str] = field(default_factory=dict)


@dataclass
class Bank(DictCompatMixin):
    country_code: str
    bic: str
    bank_code: str
    name: str
    short_name: str | None = None
    primary: bool = False
