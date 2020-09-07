#!/usr/bin/env python
import json

import requests
import xlrd


URL = "https://www.betaalvereniging.nl/wp-content/uploads/BIC-lijst-NL.xlsx"


def process():
    registry = []

    book = xlrd.open_workbook(file_contents=requests.get(URL).content)
    sheet = book.sheet_by_index(0)

    for row in list(sheet.get_rows())[2:]:
        bic, bank_code, name = row[:3]
        registry.append(
            {
                "country_code": "NL",
                "primary": True,
                "bic": bic.value.upper(),
                "bank_code": bank_code.value,
                "name": name.value,
                "short_name": name.value,
            }
        )
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_nl.json", "w") as fp:
        json.dump(process(), fp, indent=2)
