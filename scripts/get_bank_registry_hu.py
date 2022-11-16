#!/usr/bin/env python
import json

import pandas


URL = "https://www.mnb.hu/letoltes/sht.xlsx"


def process():
    registry = []
    datas = pandas.read_excel(URL, sheet_name=0, dtype="str")
    datas.fillna("", inplace=True)

    bank_codes = set()
    for row in datas.itertuples(index=False):
        code, bic, name = row[:3]

        # The branch code, which is the remainder of the `code`,  could be used to figure out the
        # correct bank name (including the branch location), but that would require to alter the
        # way banks are being looked up.
        bank_code = code[:3]
        if bank_code in bank_codes:
            continue

        bank_codes.add(bank_code)
        registry.append(
            {
                "country_code": "HU",
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
    with open("schwifty/bank_registry/generated_hu.json", "w") as fp:
        json.dump(list(process()), fp, indent=2)
