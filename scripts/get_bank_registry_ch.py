from typing import Any

import httpx2

from scripts.output import write_json
from scripts.remap import convert_to_v2


URL = "https://api.six-group.com/api/epcd/bankmaster/v3/bankmaster.json"


def fetch() -> list[dict[str, Any]]:
    return httpx2.get(URL, follow_redirects=True, timeout=None).json()["entries"]


def process(records: list[dict[str, Any]]) -> dict[str, Any]:
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
    # IID and its successor. Keep them as aliases of the successor, so that IBANs still in
    # circulation continue to resolve.
    for record in records:
        if record["entryType"] != "BankMasterConcatenated":
            continue
        successor = by_iid.get(record["newIid"])
        if successor is None:
            continue
        registry.append(
            {
                **successor,
                "bank_code": f"{record['iid']:0>5}",
                "primary": False,
                "retired": True,
                "successor_bank_code": successor["bank_code"],
            }
        )

    return convert_to_v2(registry)


if __name__ == "__main__":
    data = process(fetch())
    write_json("schwifty/bank_registry/generated_ch.v2.json", data, indent=2)
