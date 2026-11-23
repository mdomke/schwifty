#!/usr/bin/env python
import csv
import io
import re
from urllib.parse import urljoin

import httpx2
import pandas as pd
from bs4 import BeautifulSoup

from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


# Bankinfrastruktur i Sverige lists the IBAN ID and BIC of every clearing number range on this
# page. The linked file is stored under a generated path, so it is looked up on the page. It used to
# be a CSV file of the IBAN table; since November 2026 the link labelled as CSV leads to an Excel
# copy of the full clearing number master table, which also lists contact persons. Only the name,
# BIC and IBAN ID of each clearing number range are read from it.
URL = (
    "https://www.bankinfrastruktur.se/framtidens-betalningsinfrastruktur/"
    "iban-och-svenskt-nationellt-kontonummer"
)
OUTPUT = "schwifty/bank_registry/generated_se.json"
MIN_RECORDS = 30


def get_download_url():
    response = httpx2.get(URL, follow_redirects=True, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    atag = soup.find("a", href=re.compile(r"\.(csv|xlsx)$"))
    if atag is None:
        raise RuntimeError(f"CSV or Excel file not found on {URL}")
    return urljoin(URL, str(atag["href"]))


def csv_rows(content: bytes) -> list[list[str]]:
    """Return the name, BIC and IBAN ID of every row of the CSV table."""
    rows = csv.reader(io.StringIO(content.decode("utf-8-sig")), delimiter=";")
    next(rows)  # header
    return [row[1:4] for row in rows if len(row) >= 4]


EXCEL_COLUMNS = ("Aktör", "BIC", "IBAN ID")
# The master table also lists clearing numbers that aren't used for accounts, such as those of
# Bankgirocentralen, reserved ones or ones that must not be assigned. Only clearing numbers with an
# IBAN conversion method are part of the IBAN table.
IBAN_METHOD_COLUMN = "Metod IBAN konvertering"


def excel_rows(content: bytes) -> list[list[str]]:
    """Return the name ("Aktör"), BIC and IBAN ID of the master table rows that have IBANs."""
    table = pd.read_excel(io.BytesIO(content), header=None, dtype=str).fillna("")
    rows = [[cell.strip() for cell in row] for row in table.itertuples(index=False)]
    # The table starts with a legend, so the header is looked up by its titles.
    for position, row in enumerate(rows):
        if {*EXCEL_COLUMNS, IBAN_METHOD_COLUMN} <= set(row):
            columns = [row.index(title) for title in EXCEL_COLUMNS]
            method = row.index(IBAN_METHOD_COLUMN)
            return [
                [row[column] for column in columns] for row in rows[position + 1 :] if row[method]
            ]
    raise ValueError(
        f"No header row with the columns {', '.join(EXCEL_COLUMNS)} and {IBAN_METHOD_COLUMN} found"
    )


def process():
    url = get_download_url()
    print(f"Downloading {url}")
    response = httpx2.get(url, follow_redirects=True, timeout=60)
    response.raise_for_status()
    rows = (excel_rows if url.endswith(".xlsx") else csv_rows)(response.content)

    registry = {}
    primary_codes = set()
    for row in rows:
        name, bic, bank_code = row[0].strip(), row[1].strip().upper(), row[2].strip()
        if not bank_code:
            continue
        if (bank_code, bic) in registry:
            continue
        # An IBAN ID covers several clearing number ranges, which can have different BICs. The
        # one listed first is the bank's main BIC.
        registry[bank_code, bic] = {
            "country_code": "SE",
            "primary": bank_code not in primary_codes,
            "bic": bic,
            "bank_code": bank_code,
            "name": name,
            "short_name": name,
        }
        primary_codes.add(bank_code)

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the format may have changed")
    return sorted(registry.values(), key=lambda entry: entry["bank_code"])


if __name__ == "__main__":
    # The table only contains current IBAN IDs, so the previous registry is the only source for
    # those that have been removed since. Read it before replacing it.
    data = merge(process(), load_previous(OUTPUT))
    write_json(OUTPUT, data, indent=2)
