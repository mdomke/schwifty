#!/usr/bin/env python
import json

import pandas


# https://www.swedishbankers.se/fraagor-vi-arbetar-med/betalningar/ny-nordisk-betalningsinfrastruktur/iban-och-svenskt-nationellt-kontonummer/
URL = (
    "https://www.swedishbankers.se/media/4863/"
    "kalkylblad-i-iban-och-svenskt-nationellt-kontonummer-2021-02-16.xlsx"
)


def process():
    registry = []

    datas = pandas.read_excel(URL, skiprows=2, sheet_name=0, dtype=str)
    datas.fillna("", inplace=True)

    for row in datas.itertuples(index=False):
        bank_code, bic, name = row[:3]
        registry.append(
            {
                "country_code": "SE",
                "primary": True,
                "bic": str(bic).upper(),
                "bank_code": str(bank_code).split(".", 1)[0],
                "name": str(name).strip(),
                "short_name": str(name).strip(),
            }
        )

    print(f"Fetched {len(registry)} bank records")
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_se.json", "w") as fp:
        json.dump(process(), fp, indent=2)
