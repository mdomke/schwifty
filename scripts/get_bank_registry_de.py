#!/usr/bin/env python
import json
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


FIELD_LENGTHS = {
    "bank_code": 8,
    "feature": 1,
    "name": 58,
    "postal_code": 5,
    "place": 35,
    "short_name": 27,
    "pan": 5,
    "bic": 11,
    "check_digit_method": 2,
    "record_number": 6,
    "mod_number": 1,
    "tbd": 1,
    "successor_bank_code": 8,
}

URL = "https://www.bundesbank.de/de/aufgaben/unbarer-zahlungsverkehr/serviceangebot/bankleitzahlen"


def get_download_url():
    soup = BeautifulSoup(requests.get(URL).content, "html.parser")
    atag = soup.find(href=lambda ref: ref and "download-bankleitzahlen" in ref)

    soup = BeautifulSoup(requests.get(urljoin(URL, atag.get("href"))).content, "html.parser")
    atag = soup.find(href=lambda ref: ref and "blz-aktuell-txt-data.txt" in ref)
    return urljoin(URL, atag.get("href"))


def get_raw():
    return requests.get(get_download_url()).content.decode(encoding="latin1")


def parse(raw):
    for line in raw.split("\n"):
        if not line:
            continue
        record = {}
        offset = 0
        for field, length in FIELD_LENGTHS.items():
            record[field] = line[offset : offset + length].strip()
            offset = offset + length
        yield record


def process(records):
    fieldnames = ("bank_code", "name", "short_name", "bic")
    registry = []
    for record in sorted(records, key=lambda item: f'{item["bank_code"]}{item["bic"]}'):
        if not record["bank_code"]:
            continue

        cleaned = {k: v for k, v in record.items() if k in fieldnames}
        cleaned["primary"] = record["feature"] == "1"
        cleaned["country_code"] = "DE"
        cleaned["checksum_algo"] = record["check_digit_method"]

        if cleaned["bic"]:
            registry.append(cleaned)

    print(f"Fetched {len(registry)} bank records")
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_de.json", "w") as fp:
        json.dump(process(parse(get_raw())), fp, indent=2)
