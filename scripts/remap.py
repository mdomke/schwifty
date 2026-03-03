import json
import sys
from pathlib import Path
from typing import Any

from boltons.iterutils import bucketize


def convert_to_v2(
    data: list[dict[str, Any]],
    expand_from: str = "bank_codes",
    expand_into: str = "bank_code",
) -> dict[str, Any]:
    buckets = bucketize(
        data, lambda b: f"{b['bic']}::{b['name'].upper()}::{b.get('checksum_algo', '')}"
    )

    entries: list[dict[str, Any]] = []
    for _, banks in buckets.items():
        pivot = banks[0]
        pivot["bank_codes"] = [pivot.pop("bank_code")]
        pivot["name"] = pivot["name"].upper()
        pivot["short_name"] = pivot["short_name"].upper()
        for bank in banks[1:]:
            pivot["bank_codes"].append(bank["bank_code"])
        entries.append(pivot)

    return {"entries": entries, "expand_from": expand_from, "expand_into": expand_into}


if __name__ == "__main__":
    infile = Path(sys.argv[1])
    result = convert_to_v2(json.loads(infile.read_text()))

    outfile = infile.with_suffix(".v2.json")
    outfile.write_text(json.dumps(result))
