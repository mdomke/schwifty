#!/usr/bin/env python
import csv
import io
import re
from urllib.parse import urljoin

import httpx2
from bs4 import BeautifulSoup

from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


# Bankinfrastruktur i Sverige lists the IBAN ID and BIC of every clearing number range on this
# page. The linked CSV file is stored under a generated path, so it is looked up on the page.
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
    atag = soup.find("a", href=re.compile(r"\.csv$"))
    if atag is None:
        raise RuntimeError(f"CSV file not found on {URL}")
    return urljoin(URL, str(atag["href"]))


def process():
    url = get_download_url()
    print(f"Downloading {url}")
    response = httpx2.get(url, follow_redirects=True, timeout=60)
    response.raise_for_status()
    rows = csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";")
    next(rows)  # header

    registry = {}
    primary_codes = set()
    for row in rows:
        if len(row) < 4 or not row[3].strip():
            continue
        name, bic, bank_code = row[1].strip(), row[2].strip().upper(), row[3].strip()
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
