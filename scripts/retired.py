import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from schwifty.domain import BankStatus


def flatten(data: Any) -> list[dict[str, Any]]:
    """Return the entries of a v1 or v2 registry with a single ``bank_code`` each."""
    if isinstance(data, list):
        return data
    expand_from, expand_into = data["expand_from"], data["expand_into"]
    entries = []
    for entry in data["entries"]:
        values = {key: value for key, value in entry.items() if key != expand_from}
        entries.extend({**values, expand_into: value} for value in entry[expand_from])
    return entries


def load_previous(path: str | Path) -> list[dict[str, Any]]:
    """Load the registry at ``path`` as v1 entries, or nothing if it doesn't exist yet."""
    try:
        with open(path, encoding="utf-8") as fp:
            return flatten(json.load(fp))
    except FileNotFoundError:
        return []


def retire(entry: dict[str, Any], status: BankStatus = BankStatus.DELISTED) -> dict[str, Any]:
    """Return ``entry`` with ``status``, unless it already has a status other than active."""
    if entry.get("status", BankStatus.ACTIVE) != BankStatus.ACTIVE:
        return entry
    return {**entry, "status": status}


def legacy_name(entry: dict[str, Any] | None) -> str | None:
    """Return the name the bank code of ``entry`` was last listed under, if known."""
    if entry is None:
        return None
    if entry.get("status") == BankStatus.MERGED:
        return entry.get("legacy_name")
    return entry["name"]


def legacy_bic(entry: dict[str, Any] | None) -> str | None:
    """Return the BIC the bank code of ``entry`` was last listed with, if known."""
    if entry is None:
        return None
    if entry.get("status") == BankStatus.MERGED:
        return entry.get("legacy_bic")
    return entry.get("bic") or None


def alias(
    successor: dict[str, Any], bank_code: str, previous: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Return a merged entry for ``bank_code`` that leads to ``successor``.

    The entry has the successor's name and BIC, since that is the institution that services the
    bank code today. ``previous`` is the bank code's entry of the previous registry, which
    provides the name and BIC the code was last listed with, so that its BIC still resolves to
    the bank code.
    """
    entry = {
        **successor,
        "bank_code": bank_code,
        # The alias is the only record of its bank code.
        "primary": True,
        "status": BankStatus.MERGED,
        "successor_bank_code": successor["bank_code"],
    }
    name = legacy_name(previous)
    if name and name != successor["name"]:
        entry["legacy_name"] = name
    bic = legacy_bic(previous)
    if bic and bic != successor["bic"]:
        entry["legacy_bic"] = bic
    return entry


def merge(
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]],
    is_merged: Callable[[dict[str, Any]], bool] | None = None,
) -> list[dict[str, Any]]:
    """Add the bank codes of ``previous`` that have dropped out of ``current``.

    The current list is authoritative for every bank code it contains. Codes that have dropped
    out of it are kept from the previous registry, since IBANs carrying them stay in circulation.
    They are marked as delisted, unless they already have another retired status. Their
    ``primary`` flag is kept, since it only marks a bank code's main record (see ADR 3).

    Some lists keep the code of a merged bank for a while, but replace its name with a note.
    ``is_merged`` identifies such entries: they are replaced by the previous entry for their
    code, which still names the bank, and are marked as merged.
    """
    if not current:
        raise ValueError("No current bank records, refusing to mark the whole registry retired")

    known = {entry["bank_code"]: entry for entry in previous}
    # A bank code can have several BICs, so previous entries are also looked up by both.
    known_bics = {(entry["bank_code"], entry["bic"]): entry for entry in previous}
    if is_merged is not None:
        listed = []
        for entry in current:
            if is_merged(entry):
                print(f"Listed as merged {entry['bank_code']}: {entry['name']}")
                old = known_bics.get((entry["bank_code"], entry["bic"])) or known.get(
                    entry["bank_code"], entry
                )
                listed.append(retire(old, BankStatus.MERGED))
            else:
                listed.append(entry)
        current = listed
    current_codes = {entry["bank_code"] for entry in current}
    retired = sorted(
        (retire(entry) for entry in previous if entry["bank_code"] not in current_codes),
        key=lambda entry: (entry["bank_code"], entry["bic"] or ""),
    )

    # Registries that list branches have many entries with the same bank code and BIC. Name
    # changes can only be told apart where bank code and BIC identify a single entry.
    pairs = Counter((entry["bank_code"], entry["bic"]) for entry in [*previous, *current])
    for entry in current:
        pair = (entry["bank_code"], entry["bic"])
        old = known_bics.get(pair)
        if entry["bank_code"] not in known:
            print(f"Added {entry['bank_code']}: {entry['name']}")
        elif old is None:
            print(f"Updated {entry['bank_code']}: BIC {entry['bic'] or '-'} of {entry['name']}")
        elif old["name"] != entry["name"] and pairs[pair] == 2:
            print(f"Updated {entry['bank_code']}: {old['name']} -> {entry['name']}")
    for entry in retired:
        print(f"Kept {entry['status']} {entry['bank_code']}: {entry['name']}")

    print(f"Fetched {len(current)} bank records, kept {len(retired)} retired ones")
    return current + retired
