#!/usr/bin/env python
import json

import httpx2

from schwifty.domain import BankStatus
from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


BRANCH_URL = "https://bank.gov.ua/NBU_BankInfo/get_data_branch?json"
PARENT_URL = "https://bank.gov.ua/NBU_BankInfo/get_data_branch_glbank?json"
OUTPUT = "schwifty/bank_registry/generated_ua.json"
MIN_RECORDS = 1000

NORMAL = "Нормальний"
LIQUIDATION = "Ліквідація"


def split_names(s: str) -> tuple[str, str]:
    """Split the `NAME_E` field of the API into a name and a short name."""
    if " (скорочена назва - " not in s:
        return s.strip(), s.strip()
    name, short_name = (name.strip() for name in s.rstrip(")").split(" (скорочена назва - "))
    return name, short_name


def get_json(url: str) -> list[dict]:
    response = httpx2.get(url, follow_redirects=True, timeout=None)
    response.raise_for_status()
    return json.loads(response.text)


def process():
    # The National Bank of Ukraine provides English names for the banks that are still active,
    # but not for their branches, which get the English short name of their bank instead.
    short_names = {
        parent["GLMFO"]: split_names(parent["NAME_E"])[1]
        for parent in get_json(PARENT_URL)
        if parent.get("NAME_E")
    }

    registry = []
    for branch in get_json(BRANCH_URL):
        if branch["NSTAN_GOL"] == NORMAL and branch["N_STAN"] == NORMAL:
            registry.append(
                {
                    "country_code": "UA",
                    "primary": branch["TYP"] == 0,
                    "bic": "",
                    "bank_code": str(branch["MFO"]),
                    "name": branch["FULLNAME"],
                    "short_name": short_names.get(branch["GLMFO"], branch["SHORTNAME"]),
                }
            )
        elif branch["NSTAN_GOL"] == LIQUIDATION and branch["TYP"] == 0:
            # Banks in liquidation are still listed with their head office. Their codes stay
            # valid in IBANs, but the banks are closed.
            registry.append(
                {
                    "country_code": "UA",
                    "primary": True,
                    "status": BankStatus.CLOSED,
                    "bic": "",
                    "bank_code": str(branch["MFO"]),
                    "name": branch["FULLNAME"],
                    "short_name": branch["SHORTNAME"],
                }
            )

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the format may have changed")
    return registry


if __name__ == "__main__":
    # Banks that are removed from the list entirely are kept from the previous registry, which is
    # read before it is replaced.
    data = merge(process(), load_previous(OUTPUT))
    write_json(OUTPUT, data, indent=2, ensure_ascii=False)
