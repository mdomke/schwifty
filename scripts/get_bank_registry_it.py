import json
import re
from time import sleep

import requests
from bs4 import BeautifulSoup


def split_bank_name(s):
    # The patterns that might suggest the start of the short name.
    patterns = [
        r"IN FORMA ABBREVIATA",
        r"IN BREVE",
        r"IN SIGLA",
        r"ABBR\.?",
        r"O IN FORMA ABBREVIATA",
        r"OVVERO",
    ]

    for pattern in patterns:
        # Special case for the OVVERO pattern
        if pattern == r"OVVERO":
            match = re.search(rf"{pattern} ([^\(]*?) O", s)
        else:
            match = re.search(rf"{pattern} (.*?)(?=\s*(\(|,|$))", s)

        if match:
            # Short name is found in the match.
            short_name = match.group(1).strip().rstrip(")")
            # Full name is everything before the match.
            full_name = s[: match.start()]
            # Further process full_name to remove trailing keywords and extra spaces.
            for possible_end in ["O", pattern]:
                full_name = re.sub(rf"\s*{possible_end}\s*$", "", full_name).rstrip(" (")
            if "OVVERO" in short_name:
                short_name = short_name.split("OVVERO")[0].strip()
            return full_name, short_name

    # If no patterns match and the string contains a parenthesis, split at the first parenthesis.
    if "(" in s:
        return s.split("(", 1)[0].strip(), None

    # If no patterns match and no parenthesis, just return the original string and None.
    return s, None


def runtime_test_split_bank_name():
    """Run tests against split_bank_name function.

    In case there is pattern which is not covered by the function, add it to the patterns list in
    the function.
    """
    test_cases = [
        (
            "CASSA DI RISPARMIO DI FERMO S.P.A. (IN FORMA ABBREVIATA CARIFERMO S.P.A.)",
            ("CASSA DI RISPARMIO DI FERMO S.P.A.", "CARIFERMO S.P.A."),
        ),
        ("CAIXABANK S.A", ("CAIXABANK S.A", None)),
        (
            "IBL ISTITUTO BANCARIO DEL LAVORO S.P.A. (IN FORMA ABBREVIATA IBL BANCA)",
            ("IBL ISTITUTO BANCARIO DEL LAVORO S.P.A.", "IBL BANCA"),
        ),
        (
            "BANCA VALSABBINA SOCIETA' COOPERATIVA PER AZIONI (IN BREVE LA VALSABBINA)",
            ("BANCA VALSABBINA SOCIETA' COOPERATIVA PER AZIONI", "LA VALSABBINA"),
        ),
        (
            "BANCO DI BRESCIA SAN PAOLO CAB SOCIETA' PER AZIONI (ABBR. BANCO DI BRESCIA S.P.A.)",
            ("BANCO DI BRESCIA SAN PAOLO CAB SOCIETA' PER AZIONI", "BANCO DI BRESCIA S.P.A."),
        ),
        (
            "BANCA DI CIVIDALE SOCIETA' PER AZIONI O IN FORMA ABBREVIATA CIVIBANK S.P.A.",
            ("BANCA DI CIVIDALE SOCIETA' PER AZIONI", "CIVIBANK S.P.A."),
        ),
        (
            (
                "MEDIOCREDITO TRENTINO-ALTO ADIGE - S.P.A. "
                "(IN LINGUA TEDESCAINVESTITIONSBANK TRENTINO-SUDTIROL - A.G.)"
            ),
            ("MEDIOCREDITO TRENTINO-ALTO ADIGE - S.P.A.", None),
        ),
        (
            (
                "BANCA POPOLARE DELL'ETRURIA E DEL LAZIO - SOCIETA' COOPERATIVA "
                "(IN BREVE BANCAETRURIA SOCIETA' COOPERATIVA)"
            ),
            (
                "BANCA POPOLARE DELL'ETRURIA E DEL LAZIO - SOCIETA' COOPERATIVA",
                "BANCAETRURIA SOCIETA' COOPERATIVA",
            ),
        ),
        (
            (
                "CASSA DI RISPARMIO DI ASTI S.P.A. "
                "(IN FORMA ABBREVIATA BANCA C.R. ASTI S.P.A.), Filiale di Treviso"
            ),
            ("CASSA DI RISPARMIO DI ASTI S.P.A.", "BANCA C.R. ASTI S.P.A."),
        ),
        (
            (
                "BANCA PICCOLO CREDITO VALTELLINESE, SOCIETA' COOPERATIVA "
                "(OVVERO CREDITO VALTELLINESE S.C. O SOLO CREDITO VALTELLINESE)"
            ),
            (
                "BANCA PICCOLO CREDITO VALTELLINESE, SOCIETA' COOPERATIVA",
                "CREDITO VALTELLINESE S.C.",
            ),
        ),
        (
            (
                "BANCA DI CREDITO COOPERATIVO - BANCA DI SIRACUSA "
                "IN SIGLA BCC BANCA DI SIRACUSA - SOCIETA' COOPERATIVA"
            ),
            (
                "BANCA DI CREDITO COOPERATIVO - BANCA DI SIRACUSA",
                "BCC BANCA DI SIRACUSA - SOCIETA' COOPERATIVA",
            ),
        ),
    ]

    for input_str, expected_output in test_cases:
        assert split_bank_name(input_str) == expected_output

    print("test: split_bank_name passed")


def get_banks_registry_data_from_bank_name(bank_name):
    sleep(1)  # prevent server DoSing

    url = "https://www.ibancalculator.com/blz.html"
    data = {
        "tx_blz_pi1[country]": "IT",
        "tx_blz_pi1[searchterms]": bank_name,
        "tx_blz_pi1[bankcode]": "",
        "tx_blz_pi1[fi]": "fi",
        "no_cache": 1,
        "Action": "Search",
    }

    response = requests.post(url, data=data)
    soup = BeautifulSoup(response.content, "html.parser")

    results_tables = soup.select(".table")

    if results_tables:
        for row in results_tables[0].select("tr")[1:]:
            bank_code = row.select("td")[3].text
            bic = row.select("td")[2].text
            if bank_code and bic and row.select("td")[0].text == "IT":
                bank_name, bank_name_short = split_bank_name(row.select("td")[1].text)
                yield {
                    "country_code": "IT",
                    "primary": True,
                    "bic": str(bic).split(",")[0],
                    "bank_code": str(int(bank_code)).zfill(5),
                    "name": bank_name,
                    "short_name": bank_name_short or bank_name,
                }


def get_italian_bank_names():
    base_url = "https://infostat.bancaditalia.it/GIAVAInquiry-public/ng/"
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Referer": base_url,
            "Origin": "https://infostat.bancaditalia.it",
        }
    )

    # Login requests, obtains jwt token and sets cookies required for subsequent requests
    print("Logging in...")
    session.get(base_url, allow_redirects=True)
    session.post(f"{base_url}api/getElements?domainId=INQ_INT_ALBI_SUB1")

    # Get banks
    print("Getting banks...")
    response = session.post(
        f"{base_url}api/searchAllIntermediaries",
        data=json.dumps(
            {
                "searchElement": {
                    "intermediaryBoards": [
                        {
                            "boardType": {
                                "code": "001",
                                "description": "ALBO DELLE BANCHE",
                                "type": None,
                                "startDate": "1936-12-31",
                                "endDate": "9999-12-31",
                            },
                            "inscriptionProtocol": "",
                        }
                    ],
                    "establishmentDate": "2023-08-24",
                },
                "endIndex": 30,
                "startIndex": 0,
                "rowCount": 30,
                "searchOrderItems": [
                    {
                        "columnIndex": 1,
                        "insertedIndexColumn": 1,
                        "dataField": "abiCode",
                        "descending": False,
                    }
                ],
            }
        ),
        allow_redirects=True,
    )
    response.raise_for_status()
    return [x["name"] for x in response.json()]


if __name__ == "__main__":
    runtime_test_split_bank_name()

    bank_names = sorted(set(get_italian_bank_names()))
    bank_code_to_bank = {}
    for i, bank_name in enumerate(bank_names):
        print(f"{i}/{len(bank_names)}", "- ", bank_name)
        banks = get_banks_registry_data_from_bank_name(bank_name)
        for bank in banks:
            bank_code_to_bank[bank["bank_code"]] = bank

    with open("schwifty/bank_registry/generated_it.json", "w") as fp:
        json.dump(list(bank_code_to_bank.values()), fp, indent=2)
