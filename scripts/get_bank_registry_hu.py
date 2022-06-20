#!/usr/bin/env python
import json
from tempfile import NamedTemporaryFile

import openpyxl
import requests


BANK_CODES_URL = "https://www.mnb.hu/letoltes/sht.xlsx"


def process():
    yielded_bic_codes = set()

    with NamedTemporaryFile(suffix="data.xlsx") as temp_file:
        response = requests.get(BANK_CODES_URL)
        temp_file.write(response.content)
        workbook = openpyxl.load_workbook(temp_file.name)
        sheet = workbook.worksheets[0]

        for row_i, line in enumerate(sheet):
            if row_i > 1:
                bic_code = str(line[1].value).upper()
                if bic_code not in yielded_bic_codes:
                    yielded_bic_codes.add(bic_code)
                    bank_code = str(line[0].value)[:3]
                    bank_name = str(line[2].value)

                    yield {
                        "country_code": "HU",
                        "primary": True,
                        "bic": bic_code,
                        "bank_code": bank_code,
                        "name": bank_name,
                        "short_name": bank_name,
                    }


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_hu.json", "w") as fp:
        json.dump(list(process()), fp, indent=2)
