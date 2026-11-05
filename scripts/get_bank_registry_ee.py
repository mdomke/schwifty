#!/usr/bin/env python
import httpx2
from bs4 import BeautifulSoup

from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


# Eesti Pangaliit (Estonian Banking Association), "Pankade tunnuskoodid": the BIC and IBAN code of
# every bank and payment service provider in Estonia.
URL = "https://www.pangaliit.ee/arveldused/pankade-tunnuskoodid"
OUTPUT = "schwifty/bank_registry/generated_ee.json"
MIN_RECORDS = 10


def process():
    response = httpx2.get(URL, follow_redirects=True, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table")
    if table is None:
        raise RuntimeError(f"Bank code table not found on {URL}")

    registry = []
    for row in table.find_all("tr"):
        cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
        # Skip the header, empty rows and the heading of the payment service providers, which
        # have no numeric IBAN code.
        if len(cells) < 3 or not cells[2][:1].isdigit():
            continue
        name, bic, bank_codes = cells[:3]
        # Some banks have several codes, e.g. "96 / 17".
        for bank_code in bank_codes.split("/"):
            registry.append(
                {
                    "country_code": "EE",
                    "primary": True,
                    "bic": bic.upper(),
                    "bank_code": bank_code.strip().zfill(2),
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
