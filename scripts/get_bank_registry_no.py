#!/usr/bin/env python
import json

import pandas


URL = "https://www.bits.no/document/iban/"


def process():
    datas = pandas.read_excel(URL, sheet_name=0, dtype=str, header=None)
    datas.fillna("", inplace=True)

    return [
        {
            "country_code": "NO",
            "primary": True,
            "bic": str(bic).upper().strip(),
            "bank_code": bank_code,
            "name": name,
            "short_name": name,
        }
        for bank_code, bic, name in list(datas.itertuples(index=False))[1:]
        if bank_code != ""
    ]


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_no.json", "w") as fp:
        json.dump(process(), fp, indent=2)
