#!/usr/bin/env python
import io
import re
from urllib.parse import urljoin

import httpx2
import pandas
from bs4 import BeautifulSoup

from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


# Betaalvereniging Nederland, "IBAN en BIC". The spreadsheet is uploaded to a dated path with
# every update (e.g. wp-content/uploads/2026/10/BIC-lijst-NL.xlsx) and the undated URL
# redirects to a stale copy, so it is looked up on this page instead of being hard-coded.
URL = "https://www.betaalvereniging.nl/kennisbank/iban-en-bic/"
HEADERS = {"User-Agent": "schwifty registry updater (https://github.com/mdomke/schwifty)"}
BIC_PATTERN = re.compile(r"^[A-Z]{4}NL[A-Z0-9]{2}([A-Z0-9]{3})?$")
OUTPUT = "schwifty/bank_registry/generated_nl.json"
MIN_RECORDS = 10


def get_download_url():
    response = httpx2.get(URL, headers=HEADERS, follow_redirects=True, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    atag = soup.find("a", href=re.compile(r"BIC-lijst-NL\.xlsx$"))
    if atag is None:
        raise RuntimeError(f"BIC list link not found on {URL}")
    return urljoin(URL, str(atag["href"]))


def fetch():
    url = get_download_url()
    print(f"Downloading {url}")
    response = httpx2.get(url, headers=HEADERS, follow_redirects=True, timeout=60)
    response.raise_for_status()
    return response.content


def process(content):
    datas = pandas.read_excel(io.BytesIO(content), sheet_name=0, header=None, dtype=str)
    datas = datas.fillna("")
    # The title rows above the header vary between releases, so locate it by its "BIC" cell.
    header = datas.index[datas[0].str.strip().str.upper() == "BIC"]
    if header.empty:
        raise RuntimeError("Header row not found in BIC list")

    registry = []
    for row in datas.loc[header[0] + 1 :].itertuples(index=False):
        bic, bank_code, name = (str(value).strip() for value in row[:3])
        bic = bic.upper()
        if not BIC_PATTERN.match(bic):
            continue
        registry.append(
            {
                "country_code": "NL",
                "primary": True,
                "bic": bic,
                "bank_code": bank_code,
                "name": name,
                "short_name": name,
            }
        )

    if len(registry) < MIN_RECORDS:
        raise RuntimeError(f"Only {len(registry)} bank records found, the format may have changed")
    return registry


if __name__ == "__main__":
    # Read the previous registry before replacing it.
    data = merge(process(fetch()), load_previous(OUTPUT))
    write_json(OUTPUT, data, indent=2)
