#!/usr/bin/env python
"""Update the generated registries from their sources.

Runs the update script of each source, by default all sources that can be downloaded
automatically. A source that fails doesn't stop the others. After each script, its changes are
checked with :mod:`scripts.registry_diff`. If they have a problem, e.g. a source that suddenly
lists far fewer banks, the previous files are restored and the source counts as failed, unless
``--force`` is given.

    $ uv run poe update-registries          # all sources
    $ uv run poe update-registries de scl   # only some
    $ uv run poe update-registries --list   # the source names, as JSON

Lithuania (``scripts/get_bank_registry_lt.py``) and the IBAN registry
(``scripts/get_iban_registry.py``) are not included: lb.lt and swift.com reject automated
downloads, so they are updated by hand from a downloaded file.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from scripts.registry_diff import compare
from scripts.registry_diff import generated_files
from scripts.registry_diff import read_file
from scripts.registry_diff import render_text
from scripts.registry_diff import Report
from scripts.registry_diff import ROOT


# The sources that are updated automatically, mapped to the module of their update script.
SOURCES = {
    **{
        country: f"scripts.get_bank_registry_{country}"
        for country in [
            "at",
            "be",
            "ch",
            "cz",
            "de",
            "ee",
            "es",
            "fi",
            "fr",
            "gb",
            "ge",
            "hr",
            "hu",
            "it",
            "li",
            "lv",
            "nl",
            "no",
            "pl",
            "ro",
            "se",
            "si",
            "sk",
            "ua",
        ]
    },
    # The SEPA schemes of BICs, and the Irish and Maltese bank registries. It reports BICs that
    # are missing from the bank registries, so it runs after them.
    "scl": "scripts.get_scl_directory",
}

Snapshot = dict[str, bytes | None]


def snapshot() -> Snapshot:
    return {path: read_file(path) for path in generated_files()}


def restore(before: Snapshot) -> None:
    for path in set(before) | set(generated_files()):
        content = before.get(path)
        if content is None:
            (ROOT / path).unlink(missing_ok=True)
        else:
            (ROOT / path).write_bytes(content)


def update(source: str, force: bool = False) -> bool:
    """Run the update script of ``source`` and return whether its changes were kept."""
    print(f"---> Updating {source}", flush=True)
    before = snapshot()
    result = subprocess.run([sys.executable, "-m", SOURCES[source]], cwd=ROOT, check=False)  # noqa: S603
    after = snapshot()
    reports: list[Report] = [
        compare(path, before.get(path), after.get(path))
        for path in sorted(set(before) | set(after))
    ]
    print(render_text(reports), flush=True)

    if result.returncode != 0:
        print(f"---> {source}: the update script failed with exit code {result.returncode}")
        restore(before)
        return False
    if any(report.problems for report in reports):
        if force:
            print(f"---> {source}: keeping the changes despite their problems (--force)")
            return True
        print(f"---> {source}: the changes have problems and were reverted, see above")
        restore(before)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Update the generated registries.")
    parser.add_argument("sources", nargs="*", metavar="source", help="default: all sources")
    parser.add_argument(
        "--list", action="store_true", help="only print the names of the sources as JSON"
    )
    parser.add_argument("--force", action="store_true", help="keep changes that have problems")
    args = parser.parse_args()

    if unknown := [source for source in args.sources if source not in SOURCES]:
        parser.error(f"unknown sources: {', '.join(unknown)}. Choose from {', '.join(SOURCES)}")
    sources = args.sources or list(SOURCES)
    if args.list:
        print(json.dumps(sources))
        return 0
    failed = [source for source in sources if not update(source, args.force)]
    if failed:
        print(f"---> Failed: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
