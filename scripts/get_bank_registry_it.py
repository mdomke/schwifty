import json
from time import sleep

import requests
from bs4 import BeautifulSoup


def get_banks_registry_data_from_bank_name(bank_name):
    sleep(1)  # prevent server DoSing

    url = 'https://www.ibancalculator.com/blz.html'
    data = {
        'tx_blz_pi1[country]': 'IT',
        'tx_blz_pi1[searchterms]': bank_name,
        'tx_blz_pi1[bankcode]': '',
        'tx_blz_pi1[fi]': 'fi',
        'no_cache': 1,
        'Action': 'Search'
    }

    response = requests.post(url, data=data)
    soup = BeautifulSoup(response.content, "html.parser")

    results_tables = soup.select(".table")

    if results_tables:
        for row in results_tables[0].select("tr")[1:]:
            bank_code = row.select("td")[3].text
            bic = row.select("td")[2].text
            if bank_code and bic and row.select("td")[0].text == "IT":
                yield {
                    'country_code': 'IT',
                    'primary': True,
                    'bic': str(bic),
                    'bank_code': str(int(bank_code)).zfill(5),
                    'name': row.select("td")[1].text,
                    'short_name': row.select("td")[1].text,
                }


def get_italian_bank_names():
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Referer": "https://infostat.bancaditalia.it/GIAVAInquiry-public/ng/",
        "Origin": "https://infostat.bancaditalia.it",
    })

    # Login requests, obtains jwt token and sets cookies required for subsequent requests
    print("Logging in...")
    session.get("https://infostat.bancaditalia.it/GIAVAInquiry-public/ng/", allow_redirects=True)
    session.post("https://infostat.bancaditalia.it/GIAVAInquiry-public/ng/api/getElements?domainId=INQ_INT_ALBI_SUB1")

    # Get banks
    print("Getting banks...")
    response = session.post("https://infostat.bancaditalia.it/GIAVAInquiry-public/ng/api/searchAllIntermediaries", data='{"searchElement":{"intermediaryBoards":[{"boardType":{"code":"001","description":"ALBO DELLE BANCHE","type":null,"startDate":"1936-12-31","endDate":"9999-12-31"},"inscriptionProtocol":""}],"establishmentDate":"2023-08-24"},"endIndex":30,"startIndex":0,"rowCount":30,"searchOrderItems":[{"columnIndex":1,"insertedIndexColumn":1,"dataField":"abiCode","descending":false}]}', allow_redirects=True)
    response.raise_for_status()

    return [x["name"] for x in response.json()]


if __name__ == "__main__":
    bank_names = sorted(set(get_italian_bank_names()))

    bic_to_bank = {}
    for i, bank_name in enumerate(bank_names):
        print(f"{i}/{len(bank_names)}", "- ", bank_name)
        banks = get_banks_registry_data_from_bank_name(bank_name)
        for bank in banks:
            bic_to_bank[bank["bic"]] = bank

    with open("schwifty/bank_registry/generated_it.json", "w") as fp:
        json.dump(list(bic_to_bank.values()), fp, indent=2)