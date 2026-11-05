#!/usr/bin/env python

import re
from urllib.parse import urljoin

import httpx2
import pandas
from bs4 import BeautifulSoup

from scripts.output import write_json
from scripts.remap import convert_to_v2
from scripts.retired import load_previous
from scripts.retired import merge


# Finance Finland grants the MFI identifiers and lists the active ones on this page. The linked
# spreadsheet is renamed with every update (e.g. ..._in_excel_format-26032026.xlsx), so it is
# looked up by the pattern of its file name.
BASE_URL = "https://www.finanssiala.fi/en/topics/finnish-monetary-financial-institution-identifiers-and-bics/"
OUTPUT = "schwifty/bank_registry/generated_fi.v2.json"
MIN_RECORDS = 300


def process():
    response = httpx2.get(BASE_URL, follow_redirects=True, timeout=None)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    atag = soup.find("a", href=re.compile(r"monetary_institution_codes.*\.xlsx$"))
    if atag is None:
        raise RuntimeError(f"Spreadsheet link not found on {BASE_URL}")
    url = urljoin(BASE_URL, str(atag["href"]))
    print(f"Using URL: {url}")

    datas = pandas.read_excel(url, sheet_name=0, dtype=str, header=None)
    datas.fillna("", inplace=True)

    registry = [
        {
            "country_code": "FI",
            "primary": True,
            "bic": str(bic).upper().strip(),
            "bank_code": bank_code,
            "name": name,
            "short_name": name,
        }
        for bank_code, bic, name in list(datas.itertuples(index=False))[2:]
        if bank_code != ""
    ]
    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the layout may have changed")
    return registry


if __name__ == "__main__":
    # The list of Finance Finland only contains current codes, so the previous registry is the only
    # source for codes that have been removed since. Read it before replacing it.
    data = merge(process(), load_previous(OUTPUT))
    write_json(OUTPUT, convert_to_v2(data), indent=2)
