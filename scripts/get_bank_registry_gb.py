#!/usr/bin/env python
import csv
import io
import json
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from collections.abc import Iterator

import httpx2


MAPPING_URL = "https://mapping.gleif.org/api/v2/bic-lei"
LEI_RECORDS_URL = "https://api.gleif.org/api/v1/lei-records"
BATCH_SIZE = 100

# The second character of the location code marks test (0), passive (1) and reverse billing (2)
# BICs. Fully connected BICs are preferred over the others.
LOCATION_RANK = {"0": 0, "1": 1, "2": 2}


def chunked(values: Iterable[str], size: int) -> Iterator[tuple[str, ...]]:
    """Split ``values`` into tuples of at most ``size`` items.

    ``itertools.batched`` only exists from Python 3.12 on, while schwifty still supports
    Python 3.11, where importing it made this module fail with an ``ImportError``.
    """
    items = list(values)
    for start in range(0, len(items), size):
        yield tuple(items[start : start + size])


def get_download_url() -> str:
    files = httpx2.get(MAPPING_URL, follow_redirects=True, timeout=None).json()["data"]
    latest = max(
        (f for f in files if f["attributes"]["valid"]),
        key=lambda f: f["attributes"]["uploadedAt"],
    )
    return latest["attributes"]["downloadLink"]


def get_bic_lei_mapping(url: str) -> dict[str, str]:
    content = httpx2.get(url, follow_redirects=True, timeout=None).content
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".csv"))
        with archive.open(name) as fp:
            reader = csv.DictReader(io.TextIOWrapper(fp, encoding="utf-8-sig"))
            return {row["BIC"].strip().upper(): row["LEI"].strip() for row in reader}


def get_legal_names(leis: set[str]) -> dict[str, str]:
    names = {}
    for batch in chunked(sorted(leis), BATCH_SIZE):
        response = httpx2.get(
            LEI_RECORDS_URL,
            params={"filter[lei]": ",".join(batch), "page[size]": BATCH_SIZE},
            timeout=None,
        )
        for record in response.json()["data"]:
            entity = record["attributes"]["entity"]
            if entity["status"] == "ACTIVE":
                names[record["id"]] = entity["legalName"]["name"].strip()
    return names


def location_rank(bic: str) -> int:
    return LOCATION_RANK.get(bic[7], 3)


def is_primary(bic: str, bics: list[str]) -> bool:
    # GLEIF doesn't tell which of multiple BICs is the preferred one, so only mark a BIC as
    # primary if it is the single one with the best location code. Ambiguous cases have to be
    # resolved through the manual registry.
    best = max(map(location_rank, bics))
    return location_rank(bic) == best and sum(location_rank(b) == best for b in bics) == 1


def process():
    url = get_download_url()
    print(f"Using URL: {url}")

    # Only head office BICs are relevant, since the bank code of a GB IBAN is the BIC's
    # institution code and the branch is identified by the sort code instead.
    mapping = {
        bic: lei
        for bic, lei in get_bic_lei_mapping(url).items()
        if bic[4:6] == "GB" and bic.endswith("XXX")
    }
    names = get_legal_names(set(mapping.values()))

    by_bank_code = defaultdict(list)
    for bic, lei in sorted(mapping.items()):
        if lei in names:
            by_bank_code[bic[:4]].append((bic, names[lei]))

    return [
        {
            "country_code": "GB",
            "primary": is_primary(bic, [b for b, _ in entries]),
            "bic": bic,
            "bank_code": bank_code,
            "name": name,
            "short_name": name,
        }
        for bank_code, entries in sorted(by_bank_code.items())
        for bic, name in entries
    ]


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_gb.json", "w") as fp:
        json.dump(process(), fp, indent=2)
