#!/usr/bin/env python

import pandas

from scripts.output import write_json


URL = "https://www.betaalvereniging.nl/wp-content/uploads/BIC-lijst-NL.xlsx"


def process():
    registry = []

    datas = pandas.read_excel(URL, skiprows=3, sheet_name=0, dtype=str)
    datas = datas.dropna(how="all")
    datas.fillna("", inplace=True)

    for row in datas.itertuples(index=False):
        bic, bank_code, name = row[:3]

        registry.append(
            {
                "country_code": "NL",
                "primary": True,
                "bic": str(bic).upper(),
                "bank_code": bank_code,
                "name": str(name).strip(),
                "short_name": str(name).strip(),
            }
        )

    print(f"Fetched {len(registry)} bank records")
    return registry


if __name__ == "__main__":
    write_json("schwifty/bank_registry/generated_nl.json", process(), indent=2)
