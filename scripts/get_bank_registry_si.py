#!/usr/bin/env python
import io

import httpx2
import pandas

from scripts.output import write_json
from scripts.remap import convert_to_v2
from scripts.retired import alias
from scripts.retired import load_previous
from scripts.retired import merge


# Banka Slovenije, "Seznam identifikacijskih oznak ponudnikov plačilnih storitev"
# (list of national identifiers of payment service providers). The old ckfinder
# download path answers 404 since 2025; this is the document's stable address.
URL = "https://www.bsi.si/sl/d/seznam-identifikacijskih-oznak-pps"
HEADERS = {"User-Agent": "schwifty registry updater (https://github.com/mdomke/schwifty)"}
OUTPUT = "schwifty/bank_registry/generated_si.v2.json"
MIN_RECORDS = 500
# Bank code prefix of a merged institute -> prefix of its legal successor.
# 03 SKB banka, 05 and 06 Abanka were merged into Nova KBM, which became OTP banka (04) on
# 22 August 2024.
RETIRED_PREFIXES = {"03": "04", "05": "04", "06": "04"}


def process(previous):
    response = httpx2.get(URL, headers=HEADERS, follow_redirects=True, timeout=60)
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
    # merged bank as a merged alias of its successor (same approach as the Swiss registry).
    current = {entry["bank_code"] for entry in registry}
    successors = {
        prefix: next(e for e in registry if e["bank_code"].startswith(succ))
        for prefix, succ in RETIRED_PREFIXES.items()
    }
    for entry in previous:
        prefix = entry["bank_code"][:2]
        if entry["bank_code"] not in current and prefix in successors:
            registry.append(alias(successors[prefix], entry["bank_code"], entry))

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the format may have changed")
    return registry


if __name__ == "__main__":
    # Codes of other institutes that disappear from the list are kept from the previous registry,
    # which is read before it is replaced.
    previous = load_previous(OUTPUT)
    data = merge(process(previous), previous)
    write_json(OUTPUT, convert_to_v2(data), indent=2)
