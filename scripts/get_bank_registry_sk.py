#!/usr/bin/env python
import csv
import io
import re
from urllib.parse import urljoin

import httpx2
from bs4 import BeautifulSoup

from schwifty import BIC
from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


# Národná banka Slovenska, "Prevodník identifikačných kódov pre tuzemský platobný styk". The page
# links the list as PDF and CSV under generated document IDs, so the CSV is looked up on the page.
URL = "https://nbs.sk/platby/vseobecne-informacie/ciselniky-a-registre/prevodnik-sk/"
OUTPUT = "schwifty/bank_registry/generated_sk.json"
MIN_RECORDS = 20


def get_csv(client):
    response = client.get(URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    for atag in soup.find_all("a", href=re.compile(r"/dokument/.*/stiahnut")):
        response = client.get(urljoin(URL, str(atag["href"])))
        if response.is_success and response.headers.get("content-type", "").startswith("text/csv"):
            print(f"Using URL: {response.url}")
            return response.content.decode("cp1250")
    raise RuntimeError(f"CSV file not found on {URL}")


def process():
    with httpx2.Client(follow_redirects=True, timeout=60) as client:
        content = get_csv(client)

    registry = []
    for row in csv.reader(io.StringIO(content), delimiter=";"):
        # The list starts with a title and a header row, which have no numeric code.
        if len(row) < 3 or not row[0].strip().isdigit():
            continue
        bank_code, name, bic = (value.strip() for value in row[:3])
        bic = bic.upper()
        if bic and not BIC(bic, allow_invalid=True).is_valid:
            continue

        registry.append(
            {
                "country_code": "SK",
                "primary": True,
                "bic": bic,
                "bank_code": bank_code.zfill(4),
                "name": name,
                "short_name": name,
            }
        )

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the format may have changed")
    return registry


def is_run_off(entry):
    # Codes of merged banks stay on the list for a while, but the name is replaced by a note such
    # as "Československá obchodná banka, a.s. (predtým 365.bank, a.s.) - kód pre dobeh platieb".
    name = entry["name"].lower()
    return "dobeh platieb" in name or "running payments" in name


if __name__ == "__main__":
    # The list only contains current codes, so the previous registry is the only source for codes
    # that have been removed since, and for the names of banks in run-off. Read it before
    # replacing it.
    data = merge(process(), load_previous(OUTPUT), is_merged=is_run_off)
    write_json(OUTPUT, data, indent=2)
