#!/usr/bin/env python
import json

import camelot
import pandas

# https://www.bankinfrastruktur.se/framtidens-betalningsinfrastruktur/iban-och-svenskt-nationellt-kontonummer
URL = (
    "https://www.bankinfrastruktur.se/media/d1tlidv0/"
    "iban-id-och-bic-adress-for-banker-2022-06-23.pdf"
)


def process():
    registry = {}

    tables = camelot.read_pdf(URL, pages="1,2")
    datas = pandas.concat([tables[0].df, tables[1].df], ignore_index=True)

    datas.drop(index=datas.index[0], inplace=True)
    datas.drop(index=datas.index[0], inplace=True)
    datas.fillna("", inplace=True)
    datas.sort_values(1, inplace=True)
    for row in datas.itertuples(index=False):
        bank_code, bic, name = row[1:4]
        registry[str(bank_code).strip()] = {
            "country_code": "SE",
            "primary": True,
            "bic": str(bic).upper(),
            "bank_code": str(bank_code).strip(),
            "name": str(name).strip(),
            "short_name": str(name).strip(),
        }

    print(f"Fetched {len(registry)} bank records")
    return list(registry.values())


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_se.json", "w") as fp:
        json.dump(process(), fp, indent=2)
