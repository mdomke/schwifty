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

    __slots__ = ()

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


class Component(enum.StrEnum):
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
    aspirational: bool = False

    @property
    def has_positions(self) -> bool:
        """Whether the position of at least one BBAN component is known."""
        return any(not position.is_empty for position in self.positions.values())


class BankStatus(enum.StrEnum):
    """The status of a bank code in the registry."""

    #: The bank code is listed by the official source.
    ACTIVE = enum.auto()
    #: The bank was taken over or the code was replaced, so the code still leads to a successor.
    MERGED = enum.auto()
    #: The bank was closed and has no successor.
    CLOSED = enum.auto()
    #: The bank code is no longer listed by the official source, which doesn't say why.
    DELISTED = enum.auto()


@dataclass(slots=True)
class Bank(DictCompatMixin):
    """A bank record of the registry.

    A retired bank code is no longer listed by the national registry, but kept so that
    IBANs carrying it can still be identified. ``status`` tells what became of it. If the bank was
    merged, ``successor_bank_code`` names the bank code of its successor, where it is known, and
    ``name`` and ``bic`` describe the bank that services the code today, while ``legacy_name``
    and ``legacy_bic`` hold the merged bank's own name and BIC.
    """

    country_code: str
    bic: str
    bank_code: str
    name: str
    short_name: str | None = None
    primary: bool = False
    checksum_algo: str = "default"
    status: BankStatus = BankStatus.ACTIVE
    successor_bank_code: str | None = None
    legacy_name: str | None = None
    legacy_bic: str | None = None


_STATUS_RANK = {
    BankStatus.ACTIVE: 2,
    # Merged codes still lead to a successor, so they rank above closed and delisted ones.
    BankStatus.MERGED: 1,
    BankStatus.CLOSED: 0,
    BankStatus.DELISTED: 0,
}


def lookup_rank(bank: Bank) -> tuple[int, bool]:
    """Rank the records of a bank code for lookups, the best one being the highest.

    Records are ranked by their status first and by ``primary`` second, so that an active
    branch is preferred over a retired head office.
    """
    return _STATUS_RANK[bank.status], bank.primary
