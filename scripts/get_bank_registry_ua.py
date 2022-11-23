#!/usr/bin/env python
from typing import Tuple
import json
import requests
import pandas as pd

BRANCH_URL = "https://bank.gov.ua/NBU_BankInfo/get_data_branch?json"
PARENT_URL = "https://bank.gov.ua/NBU_BankInfo/get_data_branch_glbank?json"


def split_names(s) -> Tuple[str, str]:
    """This will split the `NAME_E` line from the API into a name and a short name"""
    name, short_name = [name.strip() for name in s[:-1].split(" (скорочена назва - ")]
    return name, short_name


def get_data(filter_insolvent: bool = True) -> pd.DataFrame:

    # Get raw dataframes for parent banks and branches
    with requests.get(PARENT_URL) as r:
        parents = pd.read_json(r.text)

    with requests.get(BRANCH_URL) as r:
        branches = pd.read_json(r.text)

    # Filter out insolvent branches and branches of insolvent banks
    if filter_insolvent:
        branches = branches.loc[
            (branches["N_STAN"] == "Нормальний") & (branches["NSTAN_GOL"] == "Нормальний")
        ]

    # Note that the National Bank of Ukraine provides English names for banking
    # institutions, but not for branches. Therefore we enrich the `branches`
    # dataframe with the English name for the parent bank

    # Add empty column to `branches` for full and short English name for head bank
    branches["NGOL_E"] = ""
    branches["NGOL_E_SHORT"] = ""

    for idx, row in branches.iterrows():
        # Get parent bank identifier
        glmfo = row["GLMFO"]

        # Get the name of parent bank from
        parent_names = parents.loc[parents["GLMFO"] == glmfo]["NAME_E"].iloc[0]
        parent_full_name, parent_short_name = split_names(parent_names)

        branches.loc[idx, "NGOL_E"] = parent_full_name  # type: ignore
        branches.loc[idx, "NGOL_E_SHORT"] = parent_short_name  # type: ignore

    return branches


def process():

    branches = get_data()
    registry = []

    for idx, row in branches.iterrows():

        registry.append(
            {
                "country_code": "UA",
                "primary": row["TYP"] == 0,
                "bic": None,
                "bank_code": str(row["MFO"]),
                "name": row["FULLNAME"],
                "short_name": row["NGOL_E_SHORT"],
            }
        )

    print(f"Fetched {len(registry)} bank records")
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_ua.json", "w+") as fp:
        json.dump(process(), fp, indent=2, ensure_ascii=False)
