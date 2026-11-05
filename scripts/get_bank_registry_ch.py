from typing import Any

import httpx2

from scripts.output import write_json
from scripts.remap import convert_to_v2
from scripts.retired import alias
from scripts.retired import load_previous
from scripts.retired import merge


URL = "https://api.six-group.com/api/epcd/bankmaster/v3/bankmaster.json"
OUTPUT = "schwifty/bank_registry/generated_ch.v2.json"
MIN_RECORDS = 500


def fetch() -> list[dict[str, Any]]:
    return httpx2.get(URL, follow_redirects=True, timeout=None).json()["entries"]


def process(records: list[dict[str, Any]], previous: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []
    by_iid: dict[int, dict[str, Any]] = {}

    for record in records:
        # The bank master lists every participant in Swiss payments, including foreign-based
        # banks (e.g. Deutsche Bank AG in Frankfurt), whose IIDs are valid in Swiss IBANs. Only
        # Liechtenstein banks are left out, because they have their own registry.
        if record["entryType"] != "BankMaster" or record["country"] == "LI":
            continue
        name = short_name = record["bankOrInstitutionName"]
        if name == "UBS Switzerland AG":
            name += f" - {record['townName']}"
        entry = {
            "name": name,
            "short_name": short_name,
            "bank_code": f"{record['iid']:0>5}",
            "bic": record.get("bic"),
            "country_code": "CH",
            "primary": record["iidType"] == "HEADQUARTERS",
        }
        by_iid[record["iid"]] = entry
        registry.append(entry)

    # Merged institutes are listed as BankMasterConcatenated records that only carry the retired
    # IID and its successor. Keep them as merged aliases of the successor, so that IBANs still in
    # circulation continue to resolve.
    known = {entry["bank_code"]: entry for entry in previous}
    for record in records:
        if record["entryType"] != "BankMasterConcatenated":
            continue
        successor = by_iid.get(record["newIid"])
        if successor is None:
            continue
        bank_code = f"{record['iid']:0>5}"
        registry.append(alias(successor, bank_code, known.get(bank_code)))

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records found, the bank master may have changed")
    return registry


if __name__ == "__main__":
    # Merged institutes are only listed for a while, and closed ones not at all, so the previous
    # registry is the only source for their IIDs afterwards. Read it before replacing it.
    previous = load_previous(OUTPUT)
    data = merge(process(fetch(), previous), previous)
    write_json(OUTPUT, convert_to_v2(data), indent=2)
