#!/usr/bin/env python
import json

import httpx2
from bs4 import BeautifulSoup

from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


# National Bank of Georgia, "IBAN Bank Codes". The page is rendered from the table data embedded
# in its __NEXT_DATA__ script: rows of name, BIC (RTGS code) and IBAN code.
URL = "https://nbg.gov.ge/en/payment-system/iban"
OUTPUT = "schwifty/bank_registry/generated_ge.json"
MIN_RECORDS = 10


def process():
    response = httpx2.get(URL, follow_redirects=True, timeout=60)
    response.raise_for_status()
    script = BeautifulSoup(response.content, "html.parser").find("script", id="__NEXT_DATA__")
    if script is None:
        raise RuntimeError(f"Page data not found on {URL}")
    try:
        dataset = json.loads(script.get_text())["props"]["initialProps"]["pageProps"]["dataset"]
    except (KeyError, TypeError) as e:
        raise RuntimeError(f"Bank code table not found in the page data of {URL}") from e

    registry = []
    for row in dataset[1:]:  # the first row is the header
        if len(row) < 3 or not row[2].strip():
            continue
        name, bic, bank_code = (str(value).strip() for value in row[:3])
        registry.append(
            {
                "country_code": "GE",
                "primary": True,
                "bic": bic.upper(),
                "bank_code": bank_code.upper(),
                "name": name,
                "short_name": name,
            }
        )

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the layout may have changed")
    return registry


if __name__ == "__main__":
    # The table only contains current codes, so the previous registry is the only source for codes
    # that have been removed since. Read it before replacing it.
    data = merge(process(), load_previous(OUTPUT))
    write_json(OUTPUT, data, indent=2)
