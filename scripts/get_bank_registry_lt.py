#!/usr/bin/env python
import json

import requests
from bs4 import BeautifulSoup


URL = "https://www.lb.lt/zinynai/branches.aspx"


def process():
    registry = []
    xml_content = requests.get(URL).text
    soup = BeautifulSoup(xml_content, "xml")
    participants = soup.find_all("participant")  # participants are primary bank names in LB list

    for participant in participants:
        branches = participant.find_all("branch")
        for index, branch in enumerate(branches):
            try:
                entry = {
                    "country_code": "LT",
                    "bic": participant.find("BIC").get_text(),
                    "bank_code": branch.find("FICODE").get_text(),
                    "name": branch.find("NAME").get_text(),
                    "short_name": participant.find("NAME").get_text(),
                    "primary": index == 0,
                }
                registry.append(entry)
            except AttributeError:
                pass

    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_lt.json", "w") as fp:
        json.dump(process(), fp, indent=2)
