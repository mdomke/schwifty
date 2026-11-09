#!/usr/bin/env python
"""Update the SEPA schemes of BICs and the Irish and Maltese bank registries.

The SCL directory of the Deutsche Bundesbank lists the payment service providers that can be
reached through its SEPA clearer, with the SEPA schemes each of them takes part in. It has no
bank codes, so it can only provide bank registries for countries whose IBAN bank code is part of
the BIC. For the other countries, the number of BICs that their registries lack is reported, and
with ``--report`` the BICs themselves, as a hint for their manual registries.
"""

import csv
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import httpx2

from schwifty.domain import canonical_bic
from scripts.gleif import location_rank
from scripts.output import write_json
from scripts.output import write_text
from scripts.retired import load_previous
from scripts.retired import merge


URL = "https://www.bundesbank.de/scl-directory"
OUTPUT = "schwifty/scl_registry/generated.json"
MIN_RECORDS = 4000
# The columns of the SEPA schemes. COR1, the accelerated variant of the core direct debit, was
# merged into the core direct debit in 2017.
SCHEMES = {
    "SERVICE SCT": "SCT",
    "SERVICE COR": "COR",
    "SERVICE COR1": "COR",
    "SERVICE B2B": "B2B",
    "SERVICE SCC": "SCC",
}
# Countries whose IBAN bank code is the bank code of the BIC (its first four characters).
BIC_BANK_CODE_COUNTRIES = ("IE", "MT")


def get_raw():
    response = httpx2.get(URL, follow_redirects=True, timeout=120)
    response.raise_for_status()
    return response.content.decode("latin1")


def parse(raw):
    """Return the name and SEPA schemes of every BIC in the directory."""
    lines = raw.splitlines()
    # The first line says from when the directory is valid, the second one holds the header.
    reader = csv.DictReader(io.StringIO("\n".join(lines[1:])), delimiter=";")
    missing = {"BIC", "Name", *SCHEMES} - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"Columns {sorted(missing)} not found, the format may have changed")
    directory = {}
    for row in reader:
        bic = canonical_bic(row["BIC"].strip().upper())
        if not bic:
            continue
        schemes = {scheme for column, scheme in SCHEMES.items() if row[column] == "1"}
        # A few BICs are listed in both their 8-character form and with the branch code XXX,
        # which ISO 9362 treats as the same BIC, with different schemes.
        name, known = directory.get(bic, (row["Name"].strip(), []))
        directory[bic] = (name, sorted(schemes | set(known)))
    if len(directory) < MIN_RECORDS:
        raise ValueError(f"Only {len(directory)} BICs parsed, the format may have changed")
    return directory


def dump(directory):
    """Serialize the SEPA schemes with one BIC per line, so that changes are easy to review."""
    lines = [
        f"  {json.dumps(bic)}: {json.dumps(schemes)}" for bic, (_, schemes) in directory.items()
    ]
    return "{\n" + ",\n".join(sorted(lines)) + "\n}\n"


def primary_bic(bics):
    # The BIC of the institution's primary office is preferred over branch BICs, then BICs with a
    # better location code, e.g. connected ones over passive ones.
    return min(bics, key=lambda bic: (len(bic) != 8, -location_rank(bic), bic))


def bank_registry(directory, country_code):
    """Return the bank registry of a country whose IBAN bank code is the bank code of the BIC."""
    by_bank_code = defaultdict(list)
    for bic in directory:
        if bic[4:6] == country_code:
            by_bank_code[bic[:4]].append(bic)
    registry = []
    for bank_code, bics in sorted(by_bank_code.items()):
        primary = primary_bic(bics)
        for bic in sorted(bics):
            name = directory[bic][0]
            registry.append(
                {
                    "country_code": country_code,
                    "primary": bic == primary,
                    "bic": bic,
                    "bank_code": bank_code,
                    "name": name,
                    "short_name": name,
                }
            )
    return registry


def report_missing(directory, countries, verbose=False):
    """Print the BICs of the directory that the bank registries of ``countries`` lack."""
    from schwifty import registry

    missing = defaultdict(list)
    for bic, (name, _) in sorted(directory.items()):
        country_code = bic[4:6]
        if country_code not in countries:
            continue
        if not registry.get_banks_by_bic(bic) and not registry.get_banks_by_bic(bic[:8]):
            missing[country_code].append(f"{bic} {name}")
    for country_code, entries in sorted(missing.items(), key=lambda item: -len(item[1])):
        count = f"{len(entries)} BIC{'s' if len(entries) > 1 else ''}"
        print(f"{country_code}: {count} of the SCL directory not in the registry")
        for entry in entries if verbose else []:
            print(f"  {entry}")


if __name__ == "__main__":
    directory = parse(get_raw())
    write_text(OUTPUT, dump(directory))
    print(f"Fetched the SEPA schemes of {len(directory)} BICs")

    for country_code in BIC_BANK_CODE_COUNTRIES:
        output = f"schwifty/bank_registry/generated_{country_code.lower()}.json"
        # The directory only lists current BICs, so the previous registry is the only source for
        # bank codes that have been removed since. Read it before replacing it.
        data = merge(bank_registry(directory, country_code), load_previous(output))
        write_json(output, data, indent=2)

    countries = {
        path.name.split(".")[0].rsplit("_", 1)[-1].upper()
        for path in Path("schwifty/bank_registry").glob("*.json")
    } - set(BIC_BANK_CODE_COUNTRIES)
    report_missing(directory, countries, verbose="--report" in sys.argv)
