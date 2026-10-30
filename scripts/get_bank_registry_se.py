#!/usr/bin/env python

import camelot
import pandas

from scripts.output import write_json


# https://www.bankinfrastruktur.se/framtidens-betalningsinfrastruktur/iban-och-svenskt-nationellt-kontonummer
URL = (
    "https://www.bankinfrastruktur.se/media/s0of3yyj/"
    "iban-id-och-bic-adress-for-banker-2023-09-07.pdf"
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
    write_json("schwifty/bank_registry/generated_se.json", process(), indent=2)
