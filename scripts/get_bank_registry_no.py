#!/usr/bin/env python

import pandas

from scripts.output import write_json
from scripts.remap import convert_to_v2
from scripts.retired import load_previous
from scripts.retired import merge


URL = "https://www.bits.no/document/iban/"
OUTPUT = "schwifty/bank_registry/generated_no.v2.json"
MIN_RECORDS = 1000


def process():
    datas = pandas.read_excel(URL, sheet_name=0, dtype=str, header=None)
    datas.fillna("", inplace=True)

    registry = [
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
    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the layout may have changed")
    return registry


if __name__ == "__main__":
    # The table of Bits only contains current bank codes, so the previous registry is the only
    # source for codes that have been removed since. Read it before replacing it.
    data = merge(process(), load_previous(OUTPUT))
    write_json(OUTPUT, convert_to_v2(data), indent=2)
