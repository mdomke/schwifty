import json
from typing import Any

import requests

from scripts.remap import convert_to_v2


URL = "https://api.six-group.com/api/epcd/bankmaster/v3/bankmaster.json"


def fetch() -> list[dict[str, Any]]:
    return requests.get(URL).json()["entries"]


def process(records: list[dict[str, Any]]) -> dict[str, Any]:
    registry: list[dict[str, Any]] = []

    for record in records:
        if record["entryType"] != "BankMaster" or record["country"] != "CH":
            continue
        name = short_name = record["bankOrInstitutionName"]
        if name == "UBS Switzerland AG":
            name += f" - {record['townName']}"
        registry.append(
            {
                "name": name,
                "short_name": short_name,
                "bank_code": f"{record['iid']:0>5}",
                "bic": record.get("bic"),
                "country_code": "CH",
                "primary": record["iidType"] == "HEADQUARTERS",
            }
        )
    return convert_to_v2(registry)


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_ch.v2.json", "w") as fp:
        json.dump(process(fetch()), fp, indent=2)
