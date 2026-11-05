#!/usr/bin/env python
from typing import Any

import pandas

from scripts.output import write_json
from scripts.remap import convert_to_v2
from scripts.retired import load_previous
from scripts.retired import merge


URL = "https://www.oenb.at/docroot/downloads_observ/sepa-zv-vz_gesamt.csv"
OUTPUT = "schwifty/bank_registry/generated_at.v2.json"
MIN_RECORDS = 500


def process() -> list[dict[str, Any]]:
    datas = pandas.read_csv(
        URL,
        skiprows=5,
        skip_blank_lines=True,
        encoding="latin1",
        delimiter=";",
    )
    datas = datas.dropna(how="all")
    datas = datas[datas["SWIFT-Code"].notna()]

    registry = []
    for _, row in datas.iterrows():
        if row["SWIFT-Code"] == "":
            continue
        registry.append(
            {
                "country_code": "AT",
                "primary": row["Institutsart"] == "KI",
                "bic": str(row["SWIFT-Code"]).strip().upper(),
                "bank_code": str(row["Bankleitzahl"]).strip().rjust(5, "0"),
                "name": str(row["Bankenname"]).strip(),
                "short_name": str(row["Bankenname"]).strip(),
            }
        )

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the layout may have changed")
    return registry


if __name__ == "__main__":
    # The OeNB directory only lists current institutions, so the previous registry is the only
    # source for bank codes that have been retired since. Read it before replacing it.
    data = merge(process(), load_previous(OUTPUT))
    write_json(OUTPUT, convert_to_v2(data), indent=2)
