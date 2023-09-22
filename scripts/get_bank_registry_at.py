#!/usr/bin/env python
import json
import pandas


URL = "https://www.oenb.at/docroot/downloads_observ/sepa-zv-vz_gesamt.csv"


def process():
    datas = pandas.read_csv(URL, skiprows=5, encoding="latin1", delimiter=";")
    datas = datas.dropna(how="all")
    datas.fillna("", inplace=True)

    registry = []
    for row in datas.itertuples(index=False):
        registry.append(
            {
                "country_code": "AT",
                "primary": True,
                "bic": str(row[18]).strip().upper(),
                "bank_code": str(row[2]).strip().rjust(5, "0"),
                "name": str(row[6]).strip(),
                "short_name": str(row[6]).strip(),
            }
        )

    print(f"Fetched {len(registry)} bank records")
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_at.json", "w") as fp:
        json.dump(process(), fp, indent=2)
