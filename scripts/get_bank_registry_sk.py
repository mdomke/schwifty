import csv
import json

import requests


URL = "https://www.nbs.sk/_img/Documents/_PlatobneSystemy/EUROSIPS/Directory_IC_DPS_SR.csv"


def process():
    with requests.get(URL, stream=True) as fp:
        csvfile = csv.reader([line.decode("cp1250") for line in fp.iter_lines()], delimiter=";")
    return [
        {
            "country_code": "CZ",
            "primary": True,
            "bic": row[2].strip().upper(),
            "bank_code": row[0].strip().zfill(4),
            "name": row[1].strip(),
            "short_name": row[1].strip(),
        }
        for i, row in enumerate(csvfile)
        if i >= 1
    ]


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_sk.json", "w") as fp:
        json.dump(process(), fp, indent=2)
