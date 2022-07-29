#!/usr/bin/env python
import json
import pandas


URL = (
    "https://www.bsi.si/ckfinder/connector?command=Proxy&lang=sl&type=Files&"
    "currentFolder=%2FPla%C4%8Dilni%20sistemi%2FSeznam%20identifikacijskih%20oznak%20PPS%2F&"
    "hash=6ce6c512ea433a7fc5c8841628e7696cd0ff7f2b&fileName=List-of-identifiers-of-PSP.txt"
)


def process():
    datas = pandas.read_csv(URL, encoding="latin1", delimiter=";", dtype=str)
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

    print(f"Fetched {len(registry)} bank records")
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_si.json", "w") as fp:
        json.dump(process(), fp, indent=2)
