#!/usr/bin/env python

import pandas

from scripts.output import write_json
from scripts.remap import convert_to_v2
from scripts.retired import load_previous
from scripts.retired import merge


URL = "https://www.mnb.hu/letoltes/sht.xlsx"
OUTPUT = "schwifty/bank_registry/generated_hu.v2.json"
MIN_RECORDS = 100


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

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the layout may have changed")
    return registry


if __name__ == "__main__":
    # The MNB directory only contains current branch codes, so the previous registry is the only
    # source for bank codes that have been removed since. Read it before replacing it.
    data = merge(process(), load_previous(OUTPUT))
    write_json(OUTPUT, convert_to_v2(data), indent=2)
