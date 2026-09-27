import json
from urllib.parse import urljoin

import httpx2
from bs4 import BeautifulSoup


BASE_URLS = [
    "https://www.iban.es/bancos/",
    "https://www.iban.es/bancos-extranjeros/",
    "https://www.iban.es/cajas/",
]
titles = {
    "Código de entidad (código de banco)": "bank_code",
    "Código BIC Banco (Codigo SWIFT)": "bic",
    "Denominación legal del Banco": "name",
    "Nombre Comercial (abreviado)": "short_name",
}


def get_bank_details(url):
    soup = BeautifulSoup(
        httpx2.get(url, follow_redirects=True, timeout=None).content, "html.parser"
    )
    rows = soup.select("div.about-content-text table tr")

    record = {"country_code": "ES", "primary": True}
    for row in rows:
        cells = row.find_all("td")
        if len(cells) != 2:
            continue
        title, value = cells[0].text.strip(), cells[1].text.strip()
        key = titles.get(title)
        if key:
            record[key] = value
    return record


def process():
    result = []
    for url in BASE_URLS:
        soup = BeautifulSoup(
            httpx2.get(url, follow_redirects=True, timeout=None).content, "html.parser"
        )
        paths = [str(a["href"]) for a in soup.select("h6.portfolio-title a")]
        print(f"Fetched {len(paths)} bank records")
        result.extend([get_bank_details(urljoin(url, path)) for path in paths])
    return result


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_es.json", "w") as fp:
        json.dump(process(), fp, indent=2)
