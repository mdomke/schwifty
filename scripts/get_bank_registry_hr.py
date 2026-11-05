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


# The Croatian National Bank assigns the codes and lists all payment service providers on this
# page. It replaced the former list of bank codes, which is no longer updated.
URL = "https://www.hnb.hr/en/core-functions/payment-system/bank-codes"
OUTPUT = "schwifty/bank_registry/generated_hr.json"
MIN_RECORDS = 15


def get_download_url():
    response = httpx2.get(URL, follow_redirects=True, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    atag = soup.find("a", href=re.compile(r"/documents/.*payment-service-provider-codes"))
    if atag is None:
        raise RuntimeError(f"Payment service provider code list not found on {URL}")
    return urljoin(URL, str(atag["href"]))


def process():
    url = get_download_url()
    print(f"Downloading {url}")
    response = httpx2.get(url, follow_redirects=True, timeout=60)
    response.raise_for_status()
    datas = pandas.read_excel(io.BytesIO(response.content), skiprows=3, sheet_name=0, dtype=str)
    datas.fillna("", inplace=True)

    registry = []

    for row in datas.itertuples(index=False):
        _, name, bank_code, bic = row[:4]

        registry.append(
            {
                "country_code": "HR",
                "primary": True,
                "bic": str(bic).upper().replace(" ", ""),
                "bank_code": str(bank_code).strip(),
                "name": str(name).strip(),
                "short_name": str(name).strip(),
            }
        )

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the layout may have changed")
    return registry


if __name__ == "__main__":
    # The list only contains current codes, so the previous registry is the only source for codes
    # that have been removed since. Read it before replacing it.
    data = merge(process(), load_previous(OUTPUT))
    write_json(OUTPUT, data, indent=2)
