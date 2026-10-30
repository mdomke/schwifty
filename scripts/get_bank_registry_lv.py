#!/usr/bin/env python
import io
import json
import re
from urllib.parse import urljoin

import httpx2
import pandas
from bs4 import BeautifulSoup

from scripts.output import write_json


# Latvijas Banka, "Identification of BIC by IBAN". The linked spreadsheet is renamed with
# every update (e.g. bic_saraksts_2024_ENG.xls, bic_saraksts_2026_ENG1.xls), so it is looked
# up on this page instead of being hard-coded.
URL = "https://www.bank.lv/en/operational-areas/payment-systems/identification-of-bic-by-iban"
HEADERS = {"User-Agent": "schwifty registry updater (https://github.com/mdomke/schwifty)"}
OUTPUT = "schwifty/bank_registry/generated_lv.json"
BIC_PATTERN = re.compile(r"^[A-Z]{4}LV[A-Z0-9]{2}([A-Z0-9]{3})?$")
MIN_RECORDS = 10


def get_download_url():
    response = httpx2.get(URL, headers=HEADERS, follow_redirects=True, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    links = [a for a in soup.find_all("a", href=True) if "bic_saraksts" in a["href"]]
    # Prefer the link labelled "BIC list"; the page also keeps older, unlabelled versions.
    atag = next((a for a in links if a.get_text(strip=True).lower() == "bic list"), None)
    if atag is None and links:
        atag = max(links, key=lambda a: a["href"])
    if atag is None:
        raise RuntimeError(f"BIC list link not found on {URL}")
    return urljoin(URL, str(atag["href"]))


def fetch():
    url = get_download_url()
    print(f"Downloading {url}")
    response = httpx2.get(url, headers=HEADERS, follow_redirects=True, timeout=60)
    response.raise_for_status()
    datas = pandas.read_excel(io.BytesIO(response.content), header=None, sheet_name=0, dtype=str)
    datas = datas.dropna(how="all").fillna("")

    registry = []
    for row in datas.itertuples(index=False):
        bic = str(row[3]).strip().upper()
        if bic == "BIC":  # header row
            continue
        if not BIC_PATTERN.match(bic):
            raise ValueError(f"Unexpected BIC {bic!r} in row {list(row)}")
        name = str(row[1]).strip()
        registry.append(
            {
                "country_code": "LV",
                "primary": True,
                "bic": bic,
                "bank_code": bic[:4],
                "name": name,
                "short_name": name,
            }
        )
    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the layout may have changed")
    return registry


def merge(current, previous):
    # The current list is authoritative for every bank code it contains. Codes that have
    # dropped out of it are kept from the previous registry, since IBANs carrying them stay
    # in circulation.
    known = {entry["bank_code"]: entry for entry in previous}
    current_codes = {entry["bank_code"] for entry in current}
    retired = sorted(
        (entry for entry in previous if entry["bank_code"] not in current_codes),
        key=lambda entry: entry["bank_code"],
    )

    for entry in current:
        old = known.get(entry["bank_code"])
        if old is None:
            print(f"Added {entry['bank_code']}: {entry['name']}")
        elif (old["name"], old["bic"]) != (entry["name"], entry["bic"]):
            print(f"Updated {entry['bank_code']}: {old['name']} -> {entry['name']}")
    for entry in retired:
        print(f"Kept retired {entry['bank_code']}: {entry['name']}")

    print(f"Fetched {len(current)} bank records, kept {len(retired)} retired ones")
    return current + retired


def load_previous():
    try:
        with open(OUTPUT) as fp:
            return json.load(fp)
    except FileNotFoundError:
        return []


if __name__ == "__main__":
    data = merge(fetch(), load_previous())  # read the previous file before replacing it
    write_json(OUTPUT, data, indent=2)
