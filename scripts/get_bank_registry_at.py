#!/usr/bin/env python
import json
from typing import Any

import pandas

from scripts.remap import convert_to_v2


URL = "https://www.oenb.at/docroot/downloads_observ/sepa-zv-vz_gesamt.csv"


def process() -> dict[str, Any]:
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

    print(f"Fetched {len(registry)} bank records")
    return convert_to_v2(registry)


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_at.v2.json", "w") as fp:
        json.dump(process(), fp, indent=2)
