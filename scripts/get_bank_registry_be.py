#!/usr/bin/env python
import tempfile

import httpx2
import pandas

from scripts.output import write_json
from scripts.remap import convert_to_v2
from scripts.retired import load_previous
from scripts.retired import merge


URL = "https://www.nbb.be/doc/be/be/protocol/full_list_current.xlsx"
OUTPUT = "schwifty/bank_registry/generated_be.v2.json"
MIN_RECORDS = 500


def process():
    registry = []
    skip_names = ["NAV", "VRIJ", "NAP", "NYA", "VRIJ - LIBRE", "-"]
    unassigned_names = ["VRIJ", "ONBESCHIKBAAR"]

    r = httpx2.get(URL, follow_redirects=True, timeout=None)

    with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:
        fp.write(r.content)
        datas = pandas.read_excel(fp, skiprows=1, sheet_name=0, dtype=str, engine="openpyxl")

    datas.fillna("", inplace=True)

    for row in datas.itertuples(index=False):
        bank_code, bic, name, second_name = row[:4]
        if str(bic).upper() in skip_names or str(name).upper() in unassigned_names:
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

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the layout may have changed")
    return registry


if __name__ == "__main__":
    # The NBB list marks the codes of banks that have left as free (VRIJ) and can assign them to
    # another bank later. Until it does, the previous registry is the only source for them, so it
    # is read before it is replaced.
    data = merge(process(), load_previous(OUTPUT))
    write_json(OUTPUT, convert_to_v2(data), indent=2)
