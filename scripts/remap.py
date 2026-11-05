import json
import sys
from pathlib import Path
from typing import Any
from typing import Literal
from typing import TypedDict

from boltons.iterutils import bucketize

from scripts.output import write_json


class EntryV1(TypedDict, total=False):
    name: str
    short_name: str
    bic: str | None
    bank_code: str
    primary: bool
    checksum_algo: str
    status: str
    successor_bank_code: str
    legacy_name: str
    legacy_bic: str


def convert_to_v2(
    data: list[EntryV1],
    expand_from: str = "bank_codes",
    expand_into: str = "bank_code",
    groupby: list[Literal["name", "short_name", "bic", "bank_code"]] | None = None,
) -> dict[str, Any]:
    groupby = groupby or ["bic", "name"]

    # Entries are only grouped if they agree on ``primary`` and the status fields, because the
    # group keeps the values of its first entry for all of its bank codes.
    def make_key(e: EntryV1) -> str:
        key = "::".join(str(e[group]) for group in groupby)
        status = (
            e.get("status", "active"),
            e.get("successor_bank_code"),
            e.get("legacy_name"),
            e.get("legacy_bic"),
        )
        return f"{key}::{e.get('checksum_algo', '')}::{e.get('primary', False)}::{status}"

    buckets = bucketize(data, make_key)

    entries: list[dict[str, Any]] = []
    for _, banks in buckets.items():
        pivot = banks[0]
        pivot["bank_codes"] = [pivot.pop("bank_code")]
        pivot["name"] = pivot["name"]
        pivot["short_name"] = pivot["short_name"]
        for bank in banks[1:]:
            pivot["bank_codes"].append(bank["bank_code"])
        entries.append(pivot)

    return {"entries": entries, "expand_from": expand_from, "expand_into": expand_into}


if __name__ == "__main__":
    infile = Path(sys.argv[1])
    result = convert_to_v2(json.loads(infile.read_text()))

    outfile = infile.with_suffix(".v2.json")
    write_json(outfile, result)
