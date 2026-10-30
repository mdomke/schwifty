#!/usr/bin/env python

import pandas

from scripts.output import write_json


URL = "https://www.cnb.cz/cs/platebni-styk/.galleries/ucty_kody_bank/download/kody_bank_CR.csv"


def process():
    datas = pandas.read_csv(URL, encoding="utf-8", delimiter=";", dtype="str")
    datas = datas.dropna(how="all")
    datas.fillna("", inplace=True)

    registry = []
    for row in datas.itertuples(index=False):
        registry.append(
            {
                "country_code": "CZ",
                "primary": True,
                "bic": str(row[2]).strip().upper(),
                "bank_code": str(row[0]).strip(),
                "name": str(row[1]).strip(),
                "short_name": str(row[1]).strip(),
            }
        )

    print(f"Fetched {len(registry)} bank records")
    return registry


if __name__ == "__main__":
    write_json("schwifty/bank_registry/generated_cz.json", process(), indent=2)
