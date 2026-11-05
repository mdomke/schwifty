#!/usr/bin/env python
import re
from typing import Any

import pandas

from schwifty.domain import BankStatus
from scripts.output import write_json
from scripts.remap import convert_to_v2
from scripts.retired import load_previous
from scripts.retired import merge


URL = "https://ewib.nbp.pl/plewibnra?dokNazwa=plewibnra.txt"
OUTPUT = "schwifty/bank_registry/generated_pl.v2.json"
MIN_RECORDS = 2000
# Banks in liquidation or bankruptcy are listed with a suffix to their name, e.g. "Mercedes-Benz
# Bank Polska Spółka Akcyjna w likwidacji", until their settlement numbers are removed.
WOUND_UP = re.compile(r"\bw (likwidacji|upadłości)$", re.IGNORECASE)


bic_remapping = {
    "PLUPLPRXXX": "POLUPLPRXXX",
    "POLUPLPRXX": "POLUPLPRXXX",
    "POLUPLPR": "POLUPLPRXXX",
}


def process() -> list[dict[str, Any]]:
    datas = pandas.read_csv(URL, encoding="CP852", delimiter="\t", header=None)
    datas = datas.dropna(how="all")
    datas.fillna("", inplace=True)

    registry = []
    for row in datas.itertuples(index=False):
        bic = str(row[19]).strip().upper()
        bic = bic_remapping.get(bic, bic)
        registry.append(
            {
                "country_code": "PL",
                "primary": True,
                "bic": bic,
                "bank_code": str(row[4]).strip(),
                "name": str(row[1]).strip(),
                "short_name": str(row[1]).strip(),
            }
        )

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the format may have changed")
    return registry


def close_wound_up(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mark the removed settlement numbers of banks that were wound up as closed."""
    for entry in entries:
        if entry.get("status") == BankStatus.DELISTED and WOUND_UP.search(entry["name"]):
            print(f"Closed {entry['bank_code']}: {entry['name']}")
            entry["status"] = BankStatus.CLOSED
    return entries


if __name__ == "__main__":
    # The NBP list only contains current settlement numbers, so the previous registry is the only
    # source for those that have been removed since. Read it before replacing it.
    data = close_wound_up(merge(process(), load_previous(OUTPUT)))
    write_json(OUTPUT, convert_to_v2(data), indent=2)
