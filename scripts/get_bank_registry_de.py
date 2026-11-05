#!/usr/bin/env python
import re
from urllib.parse import urljoin

import httpx2
from bs4 import BeautifulSoup

from schwifty.domain import BankStatus
from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import retire


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
MIN_RECORDS = 3000
# A bank code that the Bundesbank is going to delete names the bank code that payments are
# redirected to, if there is one.
NO_SUCCESSOR = {"", "00000000"}
# The Bundesbank marks the names of bank codes that a merger made obsolete with the suffix "-alt-"
# ("old"), e.g. "Raiffeisenbank Wismar -alt-". The status of a retired code says as much.
OLD_SUFFIX = re.compile(r"\s*-alt-?\s*$")


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


def alias(old, successor):
    """Return ``old`` as a merged bank code that resolves to the head office ``successor``."""
    # Account codes issued under the retired bank code were computed with that bank's
    # checksum method, so it is kept while name and BIC are taken from the successor. Codes
    # that were deleted before the registry recorded checksum methods have none. The bank's
    # own name and BIC are kept as well, so that it can still be identified and resolved.
    result = {**successor, "bank_code": old["bank_code"], "primary": False}
    result.pop("checksum_algo", None)
    if old.get("checksum_algo"):
        result["checksum_algo"] = old["checksum_algo"]
    result["status"] = BankStatus.MERGED
    result["successor_bank_code"] = old["successor_bank_code"]
    # An alias of the previous registry already carries the successor's name and BIC, and its
    # own ones as legacy name and BIC, if they were known.
    is_alias = "legacy_name" in old or old.get("retired")
    legacy_name = old.get("legacy_name") if is_alias else old["name"]
    legacy_bic = old.get("legacy_bic") if is_alias else old["bic"]
    if legacy_name and legacy_name != successor["name"]:
        result["legacy_name"] = legacy_name
    if legacy_bic and legacy_bic != successor["bic"]:
        result["legacy_bic"] = legacy_bic
    return result


def drop_old_suffix(entry):
    """Remove the "-alt-" suffix from the names of the bank of a retired ``entry``."""
    if entry.get("status", BankStatus.ACTIVE) == BankStatus.ACTIVE:
        return entry
    # A merged code that resolves to its successor carries the successor's names, which are left
    # as the successor's own record has them.
    fields = ["legacy_name"] if "legacy_name" in entry else ["name", "short_name"]
    for field in fields:
        if entry.get(field):
            entry[field] = OLD_SUFFIX.sub("", entry[field])
    return entry


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
    codes without a successor are kept as delisted banks, but only the head office and only if
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
            merged = {**entry(record), "successor_bank_code": successors[bank_code]}
            successor = resolve(bank_code, successors, head_offices)
            if successor is None:
                print(f"Successor of {bank_code} not found, keeping {record['name']}")
                registry.append(retire(merged, BankStatus.MERGED))
            else:
                registry.append(alias(merged, successor))
    print(f"Fetched {len(registry)} bank records, {len(successors)} merged bank codes")

    current = {item["bank_code"] for item in registry}
    carried = 0
    for old in previous:
        if old["bank_code"] in current:
            continue
        if old.get("successor_bank_code"):
            # Refresh the alias in case its successor has been renamed or merged itself.
            successor = resolve(old["successor_bank_code"], successors, head_offices)
            registry.append(alias(old, successor) if successor else old)
        elif old["primary"] and old.get("checksum_algo"):
            # Deleted banks are only kept if their account codes can still be validated.
            registry.append(retire(old))
        else:
            continue
        carried += 1
    print(f"Kept {carried} retired bank codes")

    registry = [drop_old_suffix(item) for item in registry]
    return sorted(registry, key=lambda item: f"{item['bank_code']}{item['bic']}")


if __name__ == "__main__":
    # The Bundesbank only lists current bank codes, so the previous registry is the only source for
    # deleted ones, and for the successor that was announced before the deletion. Read it before
    # replacing it.
    records = list(parse(get_raw()))
    if len(records) < MIN_RECORDS:
        raise ValueError(f"Only {len(records)} records parsed, the format may have changed")
    write_json(OUTPUT, process(records, load_previous(OUTPUT)), indent=2)
