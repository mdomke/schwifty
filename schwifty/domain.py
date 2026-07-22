from __future__ import annotations

import enum
import re
import warnings
from dataclasses import dataclass
from dataclasses import field
from typing import Any


_DICT_ACCESS_DEPRECATION = (
    "Dict-style access to {cls} objects is deprecated and will be removed in a future "
    "release. Use attribute access instead (e.g. `bank.name` instead of `bank['name']`)."
)


class DictCompatMixin:
    """Backward-compatibility shim: ``IBAN.spec`` and ``IBAN.bank`` used to return plain
    dicts, so subscription and ``.get()`` are kept working but are now deprecated in favour
    of attribute access."""

    def _warn_dict_access(self) -> None:
        warnings.warn(
            _DICT_ACCESS_DEPRECATION.format(cls=type(self).__name__),
            DeprecationWarning,
            stacklevel=3,
        )

    def __getitem__(self, key: Any) -> Any:
        self._warn_dict_access()
        if hasattr(key, "value"):
            key = key.value
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None

    def get(self, key: Any, default: Any = None) -> Any:
        self._warn_dict_access()
        if hasattr(key, "value"):
            key = key.value
        return getattr(self, key, default)


class Component(str, enum.Enum):
    ACCOUNT_ID = "account_id"
    ACCOUNT_TYPE = "account_type"
    ACCOUNT_CODE = "account_code"
    ACCOUNT_HOLDER_ID = "account_holder_id"
    CURRENCY_CODE = "currency_code"
    BANK_CODE = "bank_code"
    BRANCH_CODE = "branch_code"
    NATIONAL_CHECKSUM_DIGITS = "national_checksum_digits"


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
    checksum_algo: str = "default"
