import re
from urllib.parse import urljoin

import httpx2
from bs4 import BeautifulSoup

from schwifty.domain import BankStatus
from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


BASE_URLS = [
    "https://www.iban.es/bancos/",
    "https://www.iban.es/bancos-extranjeros/",
    "https://www.iban.es/cajas/",
]
OUTPUT = "schwifty/bank_registry/generated_es.json"
MIN_RECORDS = 400
titles = {
    "Código de entidad (código de banco)": "bank_code",
    "Código BIC Banco (Codigo SWIFT)": "bic",
    "Denominación legal del Banco": "name",
    "Nombre Comercial (abreviado)": "short_name",
    "Descripción de Cambio": "change",
    "Descripción": "description",
}

# Deregistered banks name the reason of their deregistration (e.g. "BAJA POR FUSION POR
# ABSORCION POR 2100"). Mergers, transfers of the banking business and new codes lead to a
# successor, whose code is the four-digit number in the description or the change. Dates like
# 19/07/2010 are not bank codes.
MERGED = re.compile(
    r"FUSI[OÓ]N|ABSORC|CESI[OÓ]N|TRASPASO|APORTACI[OÓ]N|TRANSMISI[OÓ]N|TRANSM\.|NUEVO C[OÓ]DIGO"
    r"|TRANSFORMACI[OÓ]N EN \d{4}"
)
UNKNOWN = re.compile(r"VARIOS MOTIVOS|REGULARIZACI[OÓ]N")
# iban.es lags behind in places: some banks that have merged since are still listed as active, and
# some active ones are missing. These corrections apply on top of it, each with its source. A
# correction that iban.es has caught up with is reported, so that it can be removed.
CORRECTIONS = {
    # CaixaBank, "CaixaBank completes legal procedures for merger with Bankia", 2021-03-26.
    "2038": {"status": BankStatus.MERGED, "successor_bank_code": "2100"},
    # Banco Santander, "Merger by absorption of Banco Popular Español", 2018-09-28.
    "0075": {"status": BankStatus.MERGED, "successor_bank_code": "0049"},
    # Unicaja Banco, "Unicaja Banco culmina la integración legal de Liberbank", 2021-07-30.
    "2048": {"status": BankStatus.MERGED, "successor_bank_code": "2103"},
    # Banco CEISS was absorbed by Unicaja Banco, merger deed signed on 2018-09-07.
    "2108": {"status": BankStatus.MERGED, "successor_bank_code": "2103"},
    # Bankia, merger by absorption of Banco Mare Nostrum registered on 2018-01-08.
    "0487": {"status": BankStatus.MERGED, "successor_bank_code": "2038"},
    # Revolut Bank UAB, Sucursal en España, registered by Banco de España on 2023-04-05
    # (BOE-A-2023-11803), but missing from iban.es.
    "1583": {"status": BankStatus.ACTIVE},
}
BANK_CODE = re.compile(r"(?<![\d/.\-])(\d{4})(?![\d/.\-])")


def get_record(client, url):
    response = client.get(url)
    if response.is_error:
        print(f"Skipping {url}: HTTP {response.status_code}")
        return None
    soup = BeautifulSoup(response.content, "html.parser")
    record = {}
    for row in soup.select("div.about-content-text table tr"):
        cells = row.find_all("td")
        if len(cells) != 2:
            continue
        title, value = cells[0].text.strip(), cells[1].text.strip()
        key = titles.get(title)
        if key:
            record[key] = value
    if not record.get("bank_code"):
        print(f"Skipping {url}: no bank code found")
        return None
    return record


def deregistration(record):
    """Return the status and the successor's bank code of a deregistered bank.

    The change describes the last event a bank was involved in, which can also be the
    deregistration of another bank. If it names the bank's own code, the bank is the one that
    absorbed the other bank, received its business or got the new code, so it is still active.
    """
    change, description = record.get("change", ""), record.get("description", "")
    codes = [code for code in BANK_CODE.findall(f"{description} {change}") if code != "0000"]
    if record["bank_code"] in codes:
        return BankStatus.ACTIVE, None
    text = f"{change} {description}".upper()
    if MERGED.search(text):
        return BankStatus.MERGED, (codes[0] if codes else None)
    if UNKNOWN.search(text):
        return BankStatus.DELISTED, None
    return BankStatus.CLOSED, None


def make_entry(record):
    entry = {
        "country_code": "ES",
        "primary": True,
        "bic": record.get("bic", ""),
        "bank_code": record["bank_code"],
        "name": record.get("name", ""),
        "short_name": record.get("short_name", ""),
    }
    # iban.es keeps deregistered banks, whose codes stay valid in IBANs. Merged banks keep their
    # own name and BIC: iban.es still lists some successors as active that have merged since
    # (e.g. Bankia), so it can't tell which bank services such a code today (see ADR 3).
    if record.get("change", "").startswith("BAJA"):
        status, successor = deregistration(record)
        if status != BankStatus.ACTIVE:
            entry["status"] = status
        if successor:
            entry["successor_bank_code"] = successor
    return entry


def process():
    registry = {}
    with httpx2.Client(follow_redirects=True, timeout=None) as client:
        for url in BASE_URLS:
            soup = BeautifulSoup(client.get(url).content, "html.parser")
            paths = [str(a["href"]) for a in soup.select("h6.portfolio-title a")]
            print(f"Found {len(paths)} banks on {url}")
            for path in paths:
                record = get_record(client, urljoin(url, path))
                if record is not None:
                    entry = make_entry(record)
                    # Some banks are listed more than once.
                    registry[tuple(entry.values())] = entry

    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the layout may have changed")
    return list(registry.values())


def correct(entries):
    """Apply ``CORRECTIONS`` to the entries of the corrected bank codes."""
    found = set()
    for entry in entries:
        correction = CORRECTIONS.get(entry["bank_code"])
        if correction is None:
            continue
        found.add(entry["bank_code"])
        current = (entry.get("status", BankStatus.ACTIVE), entry.get("successor_bank_code"))
        wanted = (correction["status"], correction.get("successor_bank_code"))
        if current == wanted:
            print(f"Correction of {entry['bank_code']} is no longer needed")
            continue
        entry.pop("status", None)
        entry.pop("successor_bank_code", None)
        if correction["status"] != BankStatus.ACTIVE:
            entry["status"] = correction["status"]
        if correction.get("successor_bank_code"):
            entry["successor_bank_code"] = correction["successor_bank_code"]
        print(f"Corrected {entry['bank_code']}: {entry['name']} is {correction['status']}")
    for bank_code in sorted(set(CORRECTIONS) - found):
        print(f"Correction of {bank_code} doesn't match any bank code")
    return entries


def resolve_successors(entries):
    """Give merged entries the name and BIC of a successor that a correction confirms.

    iban.es names the successor of every merged bank, but can't tell which bank services such a
    code today, because it still lists some successors as active that have merged themselves
    since (see ADR 3). The chain of successors is therefore only trusted if its last step comes
    from a correction, e.g. Caja Madrid -> Bankia (iban.es) -> CaixaBank (correction).
    """
    by_code = {}
    for entry in entries:
        by_code.setdefault(entry["bank_code"], entry)
    for entry in entries:
        node, seen, confirmed = entry, {entry["bank_code"]}, False
        while (
            node.get("status") == BankStatus.MERGED and node.get("successor_bank_code") in by_code
        ):
            if node["successor_bank_code"] in seen:
                break
            confirmed = node["bank_code"] in CORRECTIONS
            seen.add(node["successor_bank_code"])
            node = by_code[node["successor_bank_code"]]
        if not confirmed or node.get("status", BankStatus.ACTIVE) != BankStatus.ACTIVE:
            continue
        # Entries kept from the previous registry already carry the successor's name.
        entry.setdefault("legacy_name", entry["name"])
        entry.update(name=node["name"], short_name=node["short_name"], bic=node["bic"])
    return entries


if __name__ == "__main__":
    # Banks that are missing from iban.es, because they were removed or their page fails to
    # load, are kept from the previous registry. Read it before replacing it. The corrections
    # apply afterwards, so that they also cover such banks.
    data = resolve_successors(correct(merge(process(), load_previous(OUTPUT))))
    write_json(OUTPUT, data, indent=2)
