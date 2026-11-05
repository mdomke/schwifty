#!/usr/bin/env python
import argparse
from pathlib import Path

import httpx2
from bs4 import BeautifulSoup

from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


URL = "https://www.lb.lt/zinynai/branches.aspx"
OUTPUT = "schwifty/bank_registry/generated_lt.json"
MIN_RECORDS = 50


def get_raw():
    response = httpx2.get(URL, follow_redirects=True, timeout=None)
    if response.is_error:
        # lb.lt is behind a bot protection that rejects automated requests.
        raise RuntimeError(
            f"{URL} returned HTTP {response.status_code}. Download it in a browser and pass the "
            "path of the saved file to this script instead."
        )
    return response.text


def process(xml_content):
    registry = []
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

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the format may have changed")
    return registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Lithuanian bank registry JSON.")
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help=f"manually downloaded {URL} file; downloaded from lb.lt if omitted",
    )
    args = parser.parse_args()
    raw = args.file.read_text(encoding="utf-8") if args.file else get_raw()
    # The list only contains current codes, so the previous registry is the only source for codes
    # that have been removed since. Read it before replacing it.
    data = merge(process(raw), load_previous(OUTPUT))
    write_json(OUTPUT, data, indent=2)


if __name__ == "__main__":
    main()
