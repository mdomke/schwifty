#!/usr/bin/env python
import json
import pandas


URL = "https://www.bank.lv/images/stories/pielikumi/makssist/bic_saraksts_22.01.2020_eng.xls"


def process():
    datas = pandas.read_excel(URL, skiprows=2, sheet_name=0, dtype="str")
    datas.fillna("", inplace=True)

    return [
        {
            "country_code": "LV",
            "primary": True,
            "bic": str(bic).upper(),
            "bank_code": str(bic)[:4],
            "name": name,
            "short_name": name,
        }
        for _id, name, _iban_structure, bic in list(datas.itertuples())[2:]
    ]


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_lv.json", "w") as fp:
        json.dump(process(), fp, indent=2)
