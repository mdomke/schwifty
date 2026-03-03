#!/usr/bin/env python
import json

import pandas


URL = "https://www.oenb.at/docroot/downloads_observ/sepa-zv-vz_gesamt.csv"


def process():
    datas = pandas.read_csv(
        URL,
        skiprows=5,
        skip_blank_lines=True,
        encoding="latin1",
        delimiter=";",
    )
    datas = datas.dropna(how="all")

    registry = []
    for _, row in datas.iterrows():
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
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_at.json", "w") as fp:
        json.dump(process(), fp, indent=2)
