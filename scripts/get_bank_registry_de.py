#!/usr/bin/env python
import json
from urllib.parse import urljoin

import httpx2
from bs4 import BeautifulSoup

from scripts.output import write_json


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
    "deletion_flag": 1,
    "successor_bank_code": 8,
}

URL = "https://www.bundesbank.de/de/aufgaben/unbarer-zahlungsverkehr/serviceangebot/bankleitzahlen"
OUTPUT = "schwifty/bank_registry/generated_de.json"
NO_SUCCESSOR = {"", "00000000"}


def get_download_url():
    soup = BeautifulSoup(
        httpx2.get(URL, follow_redirects=True, timeout=None).content, "html.parser"
    )
    atag = soup.find(href=lambda ref: ref and "download-bankleitzahlen" in ref)
    if atag is None:
        raise RuntimeError(f"download link not found on {URL}")

    soup = BeautifulSoup(
        httpx2.get(urljoin(URL, atag.get("href")), follow_redirects=True, timeout=None).content,
        "html.parser",
    )
    atag = soup.find(href=lambda ref: ref and "blz-aktuell-txt-data.txt" in ref)
    if atag is None:
        raise RuntimeError("bank data file link not found in the download page")
    return urljoin(URL, atag.get("href"))


def get_raw():
    return httpx2.get(get_download_url(), follow_redirects=True, timeout=None).content.decode(
        encoding="latin1"
    )


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


def entry(record):
    return {
        "bank_code": record["bank_code"],
        "name": record["name"],
        "short_name": record["short_name"],
        "bic": record["bic"],
        "primary": record["feature"] == "1",
        "country_code": "DE",
        "checksum_algo": record["check_digit_method"],
    }


def alias(bank_code, checksum_algo, legacy_bic, successor):
    # Account codes issued under the retired bank code were computed with that bank's
    # checksum method, so it is kept while everything else is taken from the successor. Codes
    # that were deleted before the registry recorded checksum methods have none. The bank's
    # own BIC is kept as well, so that it can still be resolved.
    result = {**successor, "bank_code": bank_code, "primary": False, "retired": True}
    result.pop("checksum_algo", None)
    if checksum_algo:
        result["checksum_algo"] = checksum_algo
    result["successor_bank_code"] = successor["bank_code"]
    if legacy_bic and legacy_bic != successor["bic"]:
        result["legacy_bic"] = legacy_bic
    return result


def resolve(bank_code, successors, head_offices):
    seen = set()
    while bank_code in successors and bank_code not in seen:
        seen.add(bank_code)
        bank_code = successors[bank_code]
    return head_offices.get(bank_code)


def process(records, previous):
    """Build the registry from the Bundesbank records and the previously generated registry.

    A bank code that is announced for deletion together with a successor becomes an alias of
    the successor's head office. The Bundesbank only lists the successor until the code is
    deleted, so the aliases are carried over from the previous registry afterwards. Deleted
    codes without a successor are kept as closed banks, but only the head office and only if
    its checksum method is known.
    """
    records = [record for record in records if record["bank_code"] and record["bic"]]
    successors = {
        record["bank_code"]: record["successor_bank_code"]
        for record in records
        if record["deletion_flag"] == "1" and record["successor_bank_code"] not in NO_SUCCESSOR
    }
    head_offices = {
        record["bank_code"]: entry(record)
        for record in records
        if record["feature"] == "1" and record["bank_code"] not in successors
    }

    registry = []
    for record in records:
        bank_code = record["bank_code"]
        if bank_code not in successors:
            registry.append(entry(record))
        elif record["feature"] == "1":
            successor = resolve(bank_code, successors, head_offices)
            if successor is None:
                print(f"Successor of {bank_code} not found, keeping {record['name']}")
                registry.append(entry(record))
            else:
                registry.append(
                    alias(bank_code, record["check_digit_method"], record["bic"], successor)
                )
    print(f"Fetched {len(registry)} bank records, {len(successors)} merged bank codes")

    current = {item["bank_code"] for item in registry}
    carried = 0
    for old in previous:
        if old["bank_code"] in current:
            continue
        if "successor_bank_code" in old:
            # Refresh the alias in case its successor has been renamed or merged itself.
            successor = resolve(old["successor_bank_code"], successors, head_offices)
            registry.append(
                alias(old["bank_code"], old.get("checksum_algo"), old.get("legacy_bic"), successor)
                if successor
                else old
            )
        elif old["primary"] and old.get("checksum_algo"):
            # Closed banks are only kept if their account codes can still be validated.
            registry.append({**old, "retired": True})
        else:
            continue
        carried += 1
    print(f"Kept {carried} retired bank codes")

    return sorted(registry, key=lambda item: f"{item['bank_code']}{item['bic']}")


def load_previous():
    try:
        with open(OUTPUT) as fp:
            return json.load(fp)
    except FileNotFoundError:
        return []


if __name__ == "__main__":
    data = process(parse(get_raw()), load_previous())  # read the previous file before replacing it
    write_json(OUTPUT, data, indent=2)
