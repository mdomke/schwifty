import json

import requests
from bs4 import BeautifulSoup


BANK_CODES_URL = "https://internationalmoneytransfers.org/romania-swift-codes/"


def process():
    yielded_bic_codes = set()
    response = requests.get(BANK_CODES_URL)
    soup = BeautifulSoup(response.content, "html.parser")

    for table_row in soup.select("#tablepress-269 tr"):
        bic_code = None
        bank_name = None

        for col_i, col in enumerate(table_row.select("td")):
            if col_i == 1:
                bank_name = str(col.text)
            elif col_i == 3:
                bic_code = str(col.text)[:8]

        if bic_code and bic_code not in yielded_bic_codes:
            yielded_bic_codes.add(bic_code)
            yield {
                "country_code": "RO",
                "primary": True,
                "bic": bic_code,
                "bank_code": bic_code[:4],
                "name": bank_name,
                "short_name": bank_name,
            }


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_ro.json", "w") as fp:
        json.dump(list(process()), fp, indent=2)
