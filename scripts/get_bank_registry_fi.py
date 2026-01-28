#!/usr/bin/env python
import json

import pandas
import requests
from bs4 import BeautifulSoup


BASE_URL = (
    "https://www.finanssiala.fi/en/topics/payment-services-in-finland/payment-technical-documents/"
)


def process():
    soup = BeautifulSoup(requests.get(BASE_URL).content, "html.parser")
    url = next(
        a
        for a in soup.find_all("a")
        if a.text == "Finnish monetary institution codes and BICsin excel format"
    ).attrs["href"]
    print(f"Using URL: {url}")

    datas = pandas.read_excel(url, sheet_name=0, dtype=str, header=None)
    datas.fillna("", inplace=True)

    return [
        {
            "country_code": "FI",
            "primary": True,
            "bic": str(bic).upper().strip(),
            "bank_code": bank_code,
            "name": name,
            "short_name": name,
        }
        for bank_code, bic, name in list(datas.itertuples(index=False))[2:]
        if bank_code != ""
    ]


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_fi.json", "w") as fp:
        json.dump(process(), fp, indent=2)
