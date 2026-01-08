#!/usr/bin/env python
import json
import tempfile

import pandas
import requests


URL = "https://www.nbb.be/doc/be/be/protocol/full_list_current.xlsx"


def process():
    registry = []
    skip_names = ["NAV", "VRIJ", "NAP", "NYA", "VRIJ - LIBRE", "-"]

    r = requests.get(URL)

    with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:
        fp.write(r.content)
        datas = pandas.read_excel(fp.name, skiprows=1, sheet_name=0, dtype=str, engine="openpyxl")

    datas.fillna("", inplace=True)

    for row in datas.itertuples(index=False):
        bank_code, bic, name, second_name = row[:4]
        if str(bic).upper() in skip_names:
            continue
        registry.append(
            {
                "country_code": "BE",
                "primary": True,
                "bic": str(bic).upper().replace(" ", ""),
                "bank_code": bank_code,
                "name": name or second_name,
                "short_name": name or second_name,
            }
        )

    print(f"Fetched {len(registry)} bank records")
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_be.json", "w") as fp:
        json.dump(process(), fp, indent=2)
