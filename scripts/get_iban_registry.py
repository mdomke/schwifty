#!/usr/bin/env python
import json
import re
from typing import Any
from urllib.parse import urljoin

import httpx2
from bs4 import BeautifulSoup


COUNTRY_CODE_PATTERN = r"[A-Z]{2}"
EMPTY_RANGE = (0, 0)
URL = "https://www.swift.com/standards/data-standards/iban"

Record = dict[str, Any]


def get_raw() -> str:
    soup = BeautifulSoup(
        httpx2.get(URL, follow_redirects=True, timeout=None).content, "html.parser"
    )
    link = soup.find("a", attrs={"data-tracking-title": "IBAN Registry (TXT)"})
    return httpx2.get(
        urljoin(URL, link["href"]), follow_redirects=True, timeout=None
    ).content.decode(encoding="latin1")


def parse_int(raw: str) -> int:
    match = re.search(r"\d+", raw)
    if match:
        return int(match.group())
    return 0


def parse_range(raw: str) -> tuple[int, int]:
    pattern = r".*?(?P<from>\d+)\s*-\s*(?P<to>\d+)"
    match = re.search(pattern, raw)
    if not match:
        return EMPTY_RANGE
    return (int(match["from"]) - 1, int(match["to"]))


def parse_country_code(raw: str) -> str:
    match = re.search(COUNTRY_CODE_PATTERN, raw)
    return match.group() if match else ""


def parse(raw: str) -> list[Record]:
    columns: dict[str, list] = {}
    for line in raw.split("\r\n"):
        header, *rows = line.split("\t")
        if header == "IBAN prefix country code (ISO 3166)":
            columns["country"] = [parse_country_code(item) for item in rows]
        elif header == "Country code includes other countries/territories":
            columns["other_countries"] = [re.findall(COUNTRY_CODE_PATTERN, item) for item in rows]
        elif header == "BBAN structure":
            columns["bban_spec"] = rows
        elif header == "BBAN length":
            columns["bban_length"] = [parse_int(item) for item in rows]
        elif header == "Bank identifier position within the BBAN":
            columns["bank_code_position"] = [parse_range(item) for item in rows]
        elif header == "Branch identifier position within the BBAN":
            columns["branch_code_position"] = [parse_range(item) for item in rows]
        elif header == "IBAN structure":
            columns["iban_spec"] = rows
        elif header == "IBAN length":
            columns["iban_length"] = [parse_int(item) for item in rows]
        elif header == "SEPA country":
            columns["in_sepa_zone"] = [item.lower() == "yes" for item in rows]
    return [
        dict(zip(columns.keys(), row, strict=False)) for row in zip(*columns.values(), strict=False)
    ]


def process(records: list[Record]) -> dict[str, Record]:
    registry = {}
    for record in records:
        country_codes = [record["country"]]
        country_codes.extend(record.pop("other_countries"))
        for code in country_codes:
            registry[code] = add_positions(record)
            registry[code]["country"] = code

    return registry


def add_positions(record: Record) -> Record:
    record = dict(record)
    bank_code = record.pop("bank_code_position")
    branch_code = record.pop("branch_code_position")
    positions = {
        "account_code": (max(bank_code[1], branch_code[1]), record["bban_length"]),
        "bank_code": bank_code,
    }
    if branch_code != EMPTY_RANGE:
        positions["branch_code"] = branch_code
    record["positions"] = positions
    return record


if __name__ == "__main__":
    with open("schwifty/iban_registry/generated.json", "w+") as fp:
        json.dump(process(parse(get_raw())), fp, indent=2)
