#!/usr/bin/env python

import pandas

from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


URL = "https://www.cnb.cz/cs/platebni-styk/.galleries/ucty_kody_bank/download/kody_bank_CR.csv"
OUTPUT = "schwifty/bank_registry/generated_cz.json"
MIN_RECORDS = 30


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

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the layout may have changed")
    return registry


def is_run_off(entry):
    # During the run-off period the name is replaced by a note such as "kód užíván pro doběh
    # plateb ve prospěch Raiffeisenbank a.s. do 30. 6. 2023".
    return "doběh plateb" in entry["name"].lower()


if __name__ == "__main__":
    # The CNB code list only contains current codes. Codes of merged banks are kept for a run-off
    # period under a note naming the successor and then cancelled, so the previous registry is the
    # only source for the bank's name from then on. Read it before replacing it.
    data = merge(process(), load_previous(OUTPUT), is_merged=is_run_off)
    write_json(OUTPUT, data, indent=2)
