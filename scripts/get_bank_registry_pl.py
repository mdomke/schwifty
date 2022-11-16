#!/usr/bin/env python
import json
import pandas


URL = "https://ewib.nbp.pl/plewibnra?dokNazwa=plewibnra.txt"


bic_remapping = {
    "PLUPLPRXXX": "POLUPLPRXXX",
    "POLUPLPRXX": "POLUPLPRXXX",
    "POLUPLPR": "POLUPLPRXXX",
}


def process():
    datas = pandas.read_csv(URL, encoding="CP852", delimiter="\t", header=None)
    datas = datas.dropna(how="all")
    datas.fillna("", inplace=True)

    registry = []
    for row in datas.itertuples(index=False):
        bic = str(row[19]).strip().upper()
        bic_remapping.get(bic, bic)
        registry.append(
            {
                "country_code": "PL",
                "primary": True,
                "bic": bic,
                "bank_code": str(row[4]).strip(),
                "name": str(row[1]).strip(),
                "short_name": str(row[1]).strip(),
            }
        )

    print(f"Fetched {len(registry)} bank records")
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_pl.json", "w") as fp:
        json.dump(process(), fp, indent=2)
