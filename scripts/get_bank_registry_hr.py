#!/usr/bin/env python
import json
import pandas


URL = "https://www.hnb.hr/documents/20182/121798/tf-pp-ds-vbb-xlsx-e-vbb.xlsx/"


def process():
    datas = pandas.read_excel(URL, skiprows=3, sheet_name=0, dtype=str)
    datas.fillna("", inplace=True)

    registry = []

    for row in datas.itertuples(index=False):
        _, name, bank_code, bic = row[:4]

        registry.append(
            {
                "country_code": "HR",
                "primary": True,
                "bic": str(bic).upper().replace(" ", ""),
                "bank_code": str(bank_code),
                "name": name,
                "short_name": name,
            }
        )

    print(f"Fetched {len(registry)} bank records")
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_hr.json", "w") as fp:
        json.dump(process(), fp, indent=2)
