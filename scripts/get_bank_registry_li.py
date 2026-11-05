from typing import Any

import httpx2

from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


URL = "https://api.six-group.com/api/epcd/bankmaster/v3/bankmaster.json"
OUTPUT = "schwifty/bank_registry/generated_li.json"
MIN_RECORDS = 10


def fetch() -> list[dict[str, Any]]:
    return httpx2.get(URL, follow_redirects=True, timeout=None).json()["entries"]


def process(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []

    for record in records:
        if record["entryType"] != "BankMaster" or record["country"] != "LI":
            continue
        name = short_name = record["bankOrInstitutionName"]
        registry.append(
            {
                "name": name,
                "short_name": short_name,
                "bank_code": f"{record['iid']:0>5}",
                "bic": record.get("bic"),
                "country_code": "LI",
                "primary": record["iidType"] == "HEADQUARTERS",
            }
        )
    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records found, the bank master may have changed")
    return registry


if __name__ == "__main__":
    # The SIX bank master only lists merged institutions of Switzerland, and only for a while, so
    # the previous registry is the only source for the IIDs of Liechtenstein banks that have left.
    # Read it before replacing it.
    data = merge(process(fetch()), load_previous(OUTPUT))
    write_json(OUTPUT, data, indent=2)
