import csv
import io
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from itertools import batched
from typing import Any

import httpx2


MAPPING_URL = "https://mapping.gleif.org/api/v2/bic-lei"
LEI_RECORDS_URL = "https://api.gleif.org/api/v1/lei-records"
BATCH_SIZE = 100

# The second character of the location code marks test (0), passive (1) and reverse billing (2)
# BICs. Fully connected BICs are preferred over the others.
LOCATION_RANK = {"0": 0, "1": 1, "2": 2}


def get_download_url() -> str:
    """Return the download link of GLEIF's latest BIC-to-LEI mapping."""
    files = httpx2.get(MAPPING_URL, follow_redirects=True, timeout=None).json()["data"]
    latest = max(
        (f for f in files if f["attributes"]["valid"]),
        key=lambda f: f["attributes"]["uploadedAt"],
    )
    return latest["attributes"]["downloadLink"]


def get_bic_lei_mapping(url: str) -> dict[str, str]:
    """Return the LEI of every BIC in the mapping at ``url``."""
    content = httpx2.get(url, follow_redirects=True, timeout=None).content
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".csv"))
        with archive.open(name) as fp:
            reader = csv.DictReader(io.TextIOWrapper(fp, encoding="utf-8-sig"))
            return {row["BIC"].strip().upper(): row["LEI"].strip() for row in reader}


def get_entities(leis: Iterable[str]) -> dict[str, dict[str, Any]]:
    """Return the entity data of the LEI records of ``leis``."""
    entities = {}
    for batch in batched(sorted(set(leis)), BATCH_SIZE):
        response = httpx2.get(
            LEI_RECORDS_URL,
            params={"filter[lei]": ",".join(batch), "page[size]": BATCH_SIZE},
            timeout=None,
        )
        response.raise_for_status()
        for record in response.json()["data"]:
            entities[record["id"]] = record["attributes"]["entity"]
    return entities


def location_rank(bic: str) -> int:
    return LOCATION_RANK.get(bic[7], 3)


def is_primary(bic: str, bics: list[str]) -> bool:
    # GLEIF doesn't tell which of multiple BICs is the preferred one, so only mark a BIC as
    # primary if it is the single one with the best location code. Ambiguous cases have to be
    # resolved through the manual registry.
    best = max(map(location_rank, bics))
    return location_rank(bic) == best and sum(location_rank(b) == best for b in bics) == 1


def get_registry(country_code: str) -> list[dict[str, Any]]:
    """Return a registry entry for every head office BIC of active entities in ``country_code``.

    This only suits countries whose IBANs use the BIC's institution code as bank code (e.g. GB and
    RO). Branches are then identified by other parts of the IBAN, so only head office BICs count.
    """
    url = get_download_url()
    print(f"Using URL: {url}")
    mapping = {
        bic: lei
        for bic, lei in get_bic_lei_mapping(url).items()
        if bic[4:6] == country_code and bic.endswith("XXX")
    }
    names = {
        lei: entity["legalName"]["name"].strip()
        for lei, entity in get_entities(mapping.values()).items()
        if entity["status"] == "ACTIVE"
    }

    by_bank_code = defaultdict(list)
    for bic, lei in sorted(mapping.items()):
        if lei in names:
            by_bank_code[bic[:4]].append((bic, names[lei]))

    return [
        {
            "country_code": country_code,
            "primary": is_primary(bic, [b for b, _ in entries]),
            "bic": bic,
            "bank_code": bank_code,
            "name": name,
            "short_name": name,
        }
        for bank_code, entries in sorted(by_bank_code.items())
        for bic, name in entries
    ]
