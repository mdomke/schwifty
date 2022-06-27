#!/usr/bin/env python
import json

import requests
from bs4 import BeautifulSoup

URL = "https://www.lb.lt/zinynai/branches.aspx"

def process():
    registry = []
    xml_content = requests.get(URL).text
    soup = BeautifulSoup(xml_content, "xml")
    participants = soup.find_all("participant") # participants are primary bank names in LB list

    for participant in participants:
        branches = participant.find_all("branch")
        for index, branch in enumerate(branches):   
            try:
                if index > 0:
                    primary = False
                else:
                    primary = True
                entry = {
                    "country_code": "LT",
                    "bic": participant.find("BIC").get_text(),
                    "bank_code": branch.find("FICODE").get_text(),
                    "name": branch.find("NAME").get_text(),
                    "short_name": participant.find("NAME").get_text(),
                    "primary": primary
                }
                registry.append(entry)
            except AttributeError as e:
                pass
    
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_lt.json", "w") as fp:
        json.dump(process(), fp, indent=2)