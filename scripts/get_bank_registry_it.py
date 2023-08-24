import json

import requests
from bs4 import BeautifulSoup


def get_banks_from_response(response):
    soup = BeautifulSoup(response.content, "html.parser")

    for table_row in soup.select(".swift-country tr")[1:]:
        yield {
            "country_code": "IT",
            "primary": True,
            "bic": table_row.select(".table-swift")[0].text,
            "bank_code": table_row.select(".table-swift")[0].text[:4],
            "name": table_row.select(".table-name")[0].text,
            "short_name": table_row.select(".table-name")[0].text,
        }


def get_banks_data():
    first_page = "https://www.theswiftcodes.com/italy/"
    url = "https://www.theswiftcodes.com/italy/page/{page}/"

    yield from get_banks_from_response(requests.get(first_page))

    page = 2
    while True:
        response = requests.get(url.format(page=page))
        if response.status_code != 200:
            break
        yield from get_banks_from_response(response)
        page += 1


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_it.json", "w") as fp:
        json.dump(list(get_banks_data()), fp, indent=2)