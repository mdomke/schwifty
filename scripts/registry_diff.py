#!/usr/bin/env python
"""Summarize and check the changes an update makes to the generated registries.

The update scripts rewrite whole JSON files, so a plain diff of ``generated_de.json`` can't be
reviewed by eye. This module compares two versions of a generated registry and reports what
changed per bank code: added, retired, renamed, a new BIC or a new checksum method.

It also flags *problems* that should stop an update from being committed, e.g. a source that
suddenly lists far fewer banks. The retirement logic of the scripts (see ``scripts/retired.py``)
would otherwise mark all of their bank codes as delisted. *Warnings* are reported, but don't stop
an update.

Compare the working tree with a git revision::

    $ python -m scripts.registry_diff --base origin/main --markdown
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

from schwifty.checksum import algorithms
from schwifty.domain import BankStatus
from scripts.retired import flatten


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIRECTORIES = (
    "schwifty/bank_registry",
    "schwifty/scl_registry",
    "schwifty/iban_registry",
)

# An update may retire or drop up to this share of the previously active bank codes, but always at
# least ``MIN_ALLOWED_REMOVALS`` of them, so that a small registry can lose a bank or two.
MAX_REMOVED_SHARE = 0.05
MIN_ALLOWED_REMOVALS = 5
# The number of items per kind of change listed in a report; the rest are only counted.
MAX_LISTED = 25

BIC_PATTERN = re.compile(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?")
COUNTRY_CODE_PATTERN = re.compile(r"[A-Z]{2}")
NO_CHECKSUM_METHODS = {None, "default"}

Entry = dict[str, Any]


@dataclass
class Report:
    """The changes to one generated registry file."""

    path: str
    # Kind of change, e.g. "Added", mapped to one line per changed item.
    changes: dict[str, list[str]] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add(self, kind: str, items: Iterable[str]) -> None:
        items = list(items)
        if items:
            self.changes[kind] = items

    @property
    def changed(self) -> bool:
        return bool(self.changes or self.problems or self.warnings)


def generated_files() -> list[str]:
    """Return the paths of all generated registry files, relative to ``ROOT``."""
    root = ROOT
    return sorted(
        str(path.relative_to(root))
        for directory in REGISTRY_DIRECTORIES
        for path in (root / directory).glob("generated*.json")
    )


def removal_budget(active: int) -> int:
    """Return how many of ``active`` bank codes or entries an update may remove."""
    return max(MIN_ALLOWED_REMOVALS, int(active * MAX_REMOVED_SHARE))


def compare(path: str, old: bytes | None, new: bytes | None) -> Report:
    """Compare two versions of the generated registry at ``path``.

    ``None`` stands for a file that doesn't exist (yet).
    """
    report = Report(path)
    if new is None:
        if old is not None:
            report.problems.append("The file was deleted")
        return report
    if old == new:
        return report
    try:
        new_data = json.loads(new)
    except ValueError as e:
        report.problems.append(f"The file is not valid JSON: {e}")
        return report
    old_data = json.loads(old) if old is not None else None

    if "scl_registry" in path:
        compare_scl(report, old_data or {}, new_data)
    elif "iban_registry" in path:
        compare_iban(report, old_data or {}, new_data)
    else:
        compare_banks(report, flatten(old_data) if old_data else [], flatten(new_data))
    return report


def is_active(entry: Entry) -> bool:
    return entry.get("status", BankStatus.ACTIVE) == BankStatus.ACTIVE


def by_bank_code(entries: list[Entry]) -> dict[str, list[Entry]]:
    grouped: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        grouped[entry["bank_code"]].append(entry)
    return grouped


def describe(entries: list[Entry]) -> str:
    names = sorted({entry["name"] for entry in entries})
    return names[0] if len(names) == 1 else f"{names[0]} (+{len(names) - 1} more names)"


def values(entries: list[Entry], key: str) -> set[str]:
    return {entry[key] for entry in entries if entry.get(key)}


def show(items: set[str]) -> str:
    return ", ".join(sorted(items)) or "-"


def compare_banks(report: Report, old_entries: list[Entry], new_entries: list[Entry]) -> None:
    check_bank_entries(report, new_entries)
    old, new = by_bank_code(old_entries), by_bank_code(new_entries)

    added, dropped, retired, reactivated = [], [], [], []
    renamed, rebic, rechecksum = [], [], []
    for code in sorted(old.keys() | new.keys()):
        before, after = old.get(code), new.get(code)
        if before is None:
            added.append(f"`{code}` {describe(after)}")  # type: ignore[arg-type]
            continue
        if after is None:
            dropped.append(f"`{code}` {describe(before)}")
            continue
        was_active, is_now_active = any(map(is_active, before)), any(map(is_active, after))
        if was_active and not is_now_active:
            status = show({str(entry.get("status")) for entry in after})
            retired.append(f"`{code}` {describe(before)} ({status})")
        elif is_now_active and not was_active:
            reactivated.append(f"`{code}` {describe(after)}")
        if values(before, "name") != values(after, "name"):
            renamed.append(
                f"`{code}` {show(values(before, 'name'))} → {show(values(after, 'name'))}"
            )
        if values(before, "bic") != values(after, "bic"):
            rebic.append(f"`{code}` {show(values(before, 'bic'))} → {show(values(after, 'bic'))}")
        old_methods, new_methods = values(before, "checksum_algo"), values(after, "checksum_algo")
        if old_methods != new_methods:
            rechecksum.append(
                f"`{code}` {describe(after)}: {show(old_methods)} → {show(new_methods)}"
            )

    report.add("Added", added)
    report.add("Retired", retired)
    report.add("Reactivated", reactivated)
    report.add("Dropped", dropped)
    report.add("Renamed", renamed)
    report.add("BIC changed", rebic)
    report.add("Checksum method changed", rechecksum)

    active = sum(any(map(is_active, entries)) for entries in old.values())
    removed = len(retired) + len(dropped)
    if removed > removal_budget(active):
        report.problems.append(
            f"{removed} of {active} active bank codes were retired or dropped, more than the "
            f"{removal_budget(active)} allowed in one update. The source may be incomplete."
        )
    if dropped:
        report.warnings.append(
            f"{len(dropped)} bank codes were dropped instead of being kept as retired"
        )


def check_bank_entries(report: Report, entries: list[Entry]) -> None:
    invalid: list[str] = []
    unimplemented: dict[str, set[str]] = defaultdict(set)
    for entry in entries:
        code, bic, country_code = (
            entry.get("bank_code"),
            entry.get("bic"),
            entry.get("country_code"),
        )
        if not isinstance(code, str) or not code:
            invalid.append(f"Missing bank code: {entry}")
        elif not entry.get("name"):
            invalid.append(f"`{code}` has no name")
        elif bic and not BIC_PATTERN.fullmatch(bic):
            invalid.append(f"`{code}` has the invalid BIC {bic!r}")
        elif not COUNTRY_CODE_PATTERN.fullmatch(country_code or ""):
            invalid.append(f"`{code}` has the invalid country code {country_code!r}")
        method = entry.get("checksum_algo")
        if method not in NO_CHECKSUM_METHODS and f"{country_code}:{method}" not in algorithms:
            unimplemented[method].add(code)  # type: ignore[index]
    if invalid:
        report.problems.append(f"{len(invalid)} invalid entries")
        report.add("Invalid", invalid)
    for method, codes in sorted(unimplemented.items()):
        report.warnings.append(
            f"Checksum method `{method}` is not implemented, so account codes of "
            f"{len(codes)} bank codes are not checked: {show(set(sorted(codes)[:10]))}"
        )


def compare_scl(report: Report, old: dict[str, list[str]], new: dict[str, list[str]]) -> None:
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(bic for bic in old.keys() & new.keys() if old[bic] != new[bic])
    report.add("Added", (f"`{bic}` {', '.join(new[bic])}" for bic in added))
    report.add("Removed", (f"`{bic}`" for bic in removed))
    report.add(
        "Schemes changed",
        (f"`{bic}` {', '.join(old[bic])} → {', '.join(new[bic])}" for bic in changed),
    )
    if len(removed) > removal_budget(len(old)):
        report.problems.append(
            f"{len(removed)} of {len(old)} BICs were removed, more than the "
            f"{removal_budget(len(old))} allowed in one update. The source may be incomplete."
        )


def compare_iban(report: Report, old: dict[str, Any], new: dict[str, Any]) -> None:
    removed = sorted(old.keys() - new.keys())
    report.add("Added", sorted(new.keys() - old.keys()))
    report.add("Removed", removed)
    report.add("Changed", sorted(cc for cc in old.keys() & new.keys() if old[cc] != new[cc]))
    if removed:
        report.problems.append(f"Countries were removed: {', '.join(removed)}")


def listed(items: list[str], limit: int = MAX_LISTED) -> list[str]:
    lines = items[:limit]
    if len(items) > limit:
        lines.append(f"… and {len(items) - limit} more")
    return lines


def render_text(reports: Iterable[Report]) -> str:
    lines = []
    for report in reports:
        if not report.changed:
            continue
        lines.append(f"{report.path}:")
        lines.extend(f"  PROBLEM: {problem}" for problem in report.problems)
        lines.extend(f"  WARNING: {warning}" for warning in report.warnings)
        for kind, items in report.changes.items():
            lines.append(f"  {kind}: {len(items)}")
            lines.extend(f"    {item}" for item in listed(items))
    return "\n".join(lines) if lines else "No registry changes"


def render_markdown(reports: Iterable[Report], max_length: int | None = None) -> str:
    """Render ``reports`` as Markdown, listing fewer items per change until it fits."""
    reports = list(reports)
    limit = MAX_LISTED
    text = render_markdown_listing(reports, limit)
    while max_length is not None and len(text) > max_length and limit > 0:
        limit //= 2
        text = render_markdown_listing(reports, limit)
    return text


def render_markdown_listing(reports: Iterable[Report], limit: int) -> str:
    reports = [report for report in reports if report.changed]
    if not reports:
        return "No registry changes."
    lines = [
        "| Registry | " + " | ".join(["Changes", "Problems", "Warnings"]) + " |",
        "| --- | --- | --- | --- |",
    ]
    for report in reports:
        changes = ", ".join(
            f"{len(items)} {kind.lower()}" for kind, items in report.changes.items()
        )
        lines.append(
            f"| `{Path(report.path).name}` | {changes or '-'} | {len(report.problems) or '-'} "
            f"| {len(report.warnings) or '-'} |"
        )
    for report in reports:
        lines += ["", f"### `{Path(report.path).name}`", ""]
        lines.extend(f"> [!CAUTION]\n> {problem}\n" for problem in report.problems)
        lines.extend(f"> [!WARNING]\n> {warning}\n" for warning in report.warnings)
        for kind, items in report.changes.items():
            lines += [f"<details><summary>{kind}: {len(items)}</summary>", ""]
            lines.extend(f"- {item}" for item in listed(items, limit))
            lines += ["", "</details>"]
    return "\n".join(lines)


def read_revision(revision: str, path: str) -> bytes | None:
    result = subprocess.run(  # noqa: S603
        ["git", "show", f"{revision}:{path}"],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def revision_files(revision: str) -> list[str]:
    """Return the paths of the generated registry files at the git ``revision``."""
    result = subprocess.run(  # noqa: S603
        ["git", "ls-tree", "-r", "--name-only", revision, "--", *REGISTRY_DIRECTORIES],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    return [path for path in result.stdout.splitlines() if Path(path).name.startswith("generated")]


def read_file(path: str) -> bytes | None:
    try:
        return (ROOT / path).read_bytes()
    except FileNotFoundError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize the changes to the generated registries."
    )
    parser.add_argument("--base", default="HEAD", help="git revision to compare with")
    parser.add_argument("--markdown", action="store_true", help="render the report as Markdown")
    parser.add_argument(
        "--max-length",
        type=int,
        help="list fewer changes so that the Markdown report has at most this many characters",
    )
    args = parser.parse_args()

    paths = sorted(set(generated_files()) | set(revision_files(args.base)))
    reports = [compare(path, read_revision(args.base, path), read_file(path)) for path in paths]
    print(render_markdown(reports, args.max_length) if args.markdown else render_text(reports))
    return 1 if any(report.problems for report in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
