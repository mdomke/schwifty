#!/usr/bin/env python
import json
import pandas


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
    with open("schwifty/bank_registry/generated_nl.json", "w") as fp:
        json.dump(process(), fp, indent=2)
