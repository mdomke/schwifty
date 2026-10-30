#!/usr/bin/env python

import httpx2
import pandas

from scripts.output import write_json


URL = "https://www.bank.lv/images/stories/pielikumi/makssist/bic_saraksts_22.01.2020_eng.xls"


def process():
    agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:104.0) Gecko/20100101 Firefox/104.0"
    response = httpx2.get(URL, headers={"User-Agent": agent}, follow_redirects=True, timeout=None)

    datas = pandas.read_excel(response.content, skiprows=1, sheet_name=0, dtype="str")
    datas.fillna("", inplace=True)

    return [
        {
            "country_code": "LV",
            "primary": True,
            "bic": str(row.BIC).upper(),
            "bank_code": str(row.BIC)[:4],
            "name": row._2,
            "short_name": row._2,
        }
        for row in list(datas.itertuples())
    ]


if __name__ == "__main__":
    write_json("schwifty/bank_registry/generated_lv.json", process(), indent=2)
