#!/usr/bin/env python
import io
import json

import pandas
import requests


# Banka Slovenije, "Seznam identifikacijskih oznak ponudnikov plačilnih storitev"
# (list of national identifiers of payment service providers). The old ckfinder
# download path answers 404 since 2025; this is the document's stable address.
URL = "https://www.bsi.si/sl/d/seznam-identifikacijskih-oznak-pps"
HEADERS = {"User-Agent": "schwifty registry updater (https://github.com/mdomke/schwifty)"}
OUTPUT = "schwifty/bank_registry/generated_si.json"
# Bank code prefix of a merged institute -> prefix of its legal successor.
# 03 SKB banka and 05 Abanka were merged into Nova KBM, which became OTP banka (04) on
# 22 August 2024.
RETIRED_PREFIXES = {"03": "04", "05": "04"}


def process():
    response = requests.get(URL, headers=HEADERS, timeout=60)
    response.raise_for_status()
    datas = pandas.read_csv(
        io.StringIO(response.content.decode("cp1250")), delimiter=";", dtype=str
    )
    datas = datas.dropna(how="all")
    datas.fillna("", inplace=True)

    registry = []
    for row in datas.itertuples(index=False):
        registry.append(
            {
                "country_code": "SI",
                "primary": True,
                "bic": str(row[5]).strip().upper(),
                "bank_code": str(row[0]).strip(),
                "name": str(row[1]).strip(),
                "short_name": str(row[1]).strip(),
            }
        )

    # Codes of merged institutes disappear from the official list, but IBANs carrying them
    # stay in circulation. Keep every previously published code whose prefix belongs to a
    # merged bank as an alias of its successor (same approach as the Swiss registry).
    current = {entry["bank_code"] for entry in registry}
    successors = {
        prefix: next(e for e in registry if e["bank_code"].startswith(succ))
        for prefix, succ in RETIRED_PREFIXES.items()
    }
    for entry in load_previous():
        prefix = entry["bank_code"][:2]
        if entry["bank_code"] not in current and prefix in successors:
            registry.append(
                {**successors[prefix], "bank_code": entry["bank_code"], "primary": False}
            )

    print(f"Fetched {len(registry)} bank records")
    return registry


def load_previous():
    try:
        with open(OUTPUT) as fp:
            return json.load(fp)
    except FileNotFoundError:
        return []


if __name__ == "__main__":
    data = process()  # read the previous file before opening it for writing
    with open(OUTPUT, "w") as fp:
        json.dump(data, fp, indent=2)
