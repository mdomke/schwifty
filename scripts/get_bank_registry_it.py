import json
import re
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import date
from datetime import datetime
from datetime import UTC

import httpx2

from schwifty.domain import BankStatus
from scripts.gleif import get_bic_lei_mapping
from scripts.gleif import get_download_url
from scripts.gleif import get_entities
from scripts.gleif import location_rank
from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


# Banca d'Italia's registers of banks, e-money institutions and payment institutions. They can be
# queried as of any date, which yields both the active institutions and those that have ceased
# since FIRST_YEAR, with ABI code and name.
GIAVA_URL = "https://infostat.bancaditalia.it/GIAVAInquiry-public/ng/"
BOARDS = {
    "001": "ALBO DELLE BANCHE",
    "016": "ALBO IMEL ITA EX 114-QUATER",
    "012": "ALBO IP ART.114-SEPTIES TUB",
}
# The register doesn't contain BICs. They are taken from GLEIF's BIC-to-LEI mapping instead,
# whose LEI records carry the same Italian tax code as the register.
OUTPUT = "schwifty/bank_registry/generated_it.json"
FIRST_YEAR = 2008
MIN_RECORDS = 300
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Referer": GIAVA_URL,
    "Origin": "https://infostat.bancaditalia.it",
}
# The history of an institution that has ceased names the bank it was absorbed into, merged with or
# sold its business to, e.g. "Incorporazione in 3069 - INTESA SANPAOLO S.P.A.".
SUCCESSION = re.compile(
    r"^(?:Incorporazione in|Fusione con|Cessione attivita' e passivita' a) (\d+) - "
)
# Causes of the cancellation from a register after which the institution has no successor: the
# license was renounced, the institution was liquidated (voluntarily or compulsorily), the
# supervisory authority ordered it, the license was forfeited or the activity revoked. Other causes,
# such as a structural event between institutions that has no successor in Italy, are unspecific.
CLOSING_CAUSES = {"001", "002", "003", "004", "008", "012"}


def split_bank_name(s):
    # The patterns that might suggest the start of the short name.
    patterns = [
        r"IN FORMA ABBREVIATA",
        r"IN FORMA CONTRATTA",
        r"IN BREVE",
        r"IN SIGLA",
        r"ABBR\.?",
        r"O IN FORMA ABBREVIATA",
        r"OVVERO",
    ]

    matches = []
    for pattern in patterns:
        # Special case for the OVVERO pattern
        if pattern == r"OVVERO":
            match = re.search(rf"{pattern} ([^\(]*?) O", s)
        else:
            match = re.search(rf"{pattern} (.*?)(?=\s*(\(|,|$))", s)
        if match:
            matches.append((match.start(), pattern, match))

    # A name can contain several of the patterns, e.g. "BANCA IFIS S.P.A. (OVVERO IFIS BANCA S.P.A.
    # O IN FORMA ABBREVIATA IFIS S.P.A.)". The full name ends before the first of them, and the
    # short name is taken from the pattern that comes first in the list, the abbreviated form.
    if matches:
        # Short name is found in the match.
        short_name = matches[0][2].group(1).strip().rstrip(")")
        # Full name is everything before the first match.
        _, pattern, match = min(matches, key=lambda item: item[0])
        full_name = s[: match.start()]
        # Further process full_name to remove trailing keywords and extra spaces.
        for possible_end in ["O", pattern]:
            # The word boundary keeps a trailing O of the name itself, e.g. of MILANO.
            full_name = re.sub(rf"\s*\b{possible_end}\s*$", "", full_name).rstrip(" (")
        if "OVVERO" in short_name:
            short_name = short_name.split("OVVERO")[0].strip()
        return full_name, short_name

    # If no patterns match and the string contains a parenthesis, split at the first parenthesis.
    if "(" in s:
        return s.split("(", 1)[0].strip(), None

    # If no patterns match and no parenthesis, just return the original string and None.
    return s, None


def runtime_test_split_bank_name():
    """Run tests against split_bank_name function.

    In case there is pattern which is not covered by the function, add it to the patterns list in
    the function.
    """
    test_cases = [
        (
            "CASSA DI RISPARMIO DI FERMO S.P.A. (IN FORMA ABBREVIATA CARIFERMO S.P.A.)",
            ("CASSA DI RISPARMIO DI FERMO S.P.A.", "CARIFERMO S.P.A."),
        ),
        ("CAIXABANK S.A", ("CAIXABANK S.A", None)),
        (
            "BANCA NAZIONALE DEL LAVORO S.P.A. (IN FORMA CONTRATTA BNL S.P.A.)",
            ("BANCA NAZIONALE DEL LAVORO S.P.A.", "BNL S.P.A."),
        ),
        (
            "IBL ISTITUTO BANCARIO DEL LAVORO S.P.A. (IN FORMA ABBREVIATA IBL BANCA)",
            ("IBL ISTITUTO BANCARIO DEL LAVORO S.P.A.", "IBL BANCA"),
        ),
        (
            "BANCA VALSABBINA SOCIETA' COOPERATIVA PER AZIONI (IN BREVE LA VALSABBINA)",
            ("BANCA VALSABBINA SOCIETA' COOPERATIVA PER AZIONI", "LA VALSABBINA"),
        ),
        (
            "BANCO DI BRESCIA SAN PAOLO CAB SOCIETA' PER AZIONI (ABBR. BANCO DI BRESCIA S.P.A.)",
            ("BANCO DI BRESCIA SAN PAOLO CAB SOCIETA' PER AZIONI", "BANCO DI BRESCIA S.P.A."),
        ),
        (
            "BANCA DI CIVIDALE SOCIETA' PER AZIONI O IN FORMA ABBREVIATA CIVIBANK S.P.A.",
            ("BANCA DI CIVIDALE SOCIETA' PER AZIONI", "CIVIBANK S.P.A."),
        ),
        (
            (
                "MEDIOCREDITO TRENTINO-ALTO ADIGE - S.P.A. "
                "(IN LINGUA TEDESCAINVESTITIONSBANK TRENTINO-SUDTIROL - A.G.)"
            ),
            ("MEDIOCREDITO TRENTINO-ALTO ADIGE - S.P.A.", None),
        ),
        (
            (
                "BANCA POPOLARE DELL'ETRURIA E DEL LAZIO - SOCIETA' COOPERATIVA "
                "(IN BREVE BANCAETRURIA SOCIETA' COOPERATIVA)"
            ),
            (
                "BANCA POPOLARE DELL'ETRURIA E DEL LAZIO - SOCIETA' COOPERATIVA",
                "BANCAETRURIA SOCIETA' COOPERATIVA",
            ),
        ),
        (
            (
                "CASSA DI RISPARMIO DI ASTI S.P.A. "
                "(IN FORMA ABBREVIATA BANCA C.R. ASTI S.P.A.), Filiale di Treviso"
            ),
            ("CASSA DI RISPARMIO DI ASTI S.P.A.", "BANCA C.R. ASTI S.P.A."),
        ),
        (
            (
                "BANCA PICCOLO CREDITO VALTELLINESE, SOCIETA' COOPERATIVA "
                "(OVVERO CREDITO VALTELLINESE S.C. O SOLO CREDITO VALTELLINESE)"
            ),
            (
                "BANCA PICCOLO CREDITO VALTELLINESE, SOCIETA' COOPERATIVA",
                "CREDITO VALTELLINESE S.C.",
            ),
        ),
        (
            "BANK OF CHINA LIMITED - FILIALE DI MILANO O IN FORMA ABBREVIATA BANK OF CHINA",
            ("BANK OF CHINA LIMITED - FILIALE DI MILANO", "BANK OF CHINA"),
        ),
        (
            "BANCA IFIS S.P.A. (OVVERO IFIS BANCA S.P.A. O IN FORMA ABBREVIATA IFIS S.P.A.)",
            ("BANCA IFIS S.P.A.", "IFIS S.P.A."),
        ),
        (
            (
                "BANCA DI CREDITO COOPERATIVO - BANCA DI SIRACUSA "
                "IN SIGLA BCC BANCA DI SIRACUSA - SOCIETA' COOPERATIVA"
            ),
            (
                "BANCA DI CREDITO COOPERATIVO - BANCA DI SIRACUSA",
                "BCC BANCA DI SIRACUSA - SOCIETA' COOPERATIVA",
            ),
        ),
    ]

    for input_str, expected_output in test_cases:
        assert split_bank_name(input_str) == expected_output

    print("test: split_bank_name passed")


@contextmanager
def get_client():
    with httpx2.Client(headers=HEADERS, follow_redirects=True, timeout=None) as client:
        # Obtains the token and cookies required for the subsequent requests.
        client.get(GIAVA_URL)
        client.post(f"{GIAVA_URL}api/getElements?domainId=INQ_INT_ALBI_SUB1")
        client.post(f"{GIAVA_URL}api/getElements?domainId=INQ_INT_ALBI_SUB4")
        yield client


def get_registers(client, dates):
    """Return the institutions in Banca d'Italia's registers as of each of ``dates``."""
    registers = {}
    for day in dates:
        print(f"Getting banks as of {day}...")
        response = client.post(
            f"{GIAVA_URL}api/searchAllIntermediaries",
            content=json.dumps(
                {
                    "searchElement": {
                        "intermediaryBoards": [
                            {
                                "boardType": {
                                    "code": code,
                                    "description": description,
                                    "type": None,
                                    "startDate": "1936-12-31",
                                    "endDate": "9999-12-31",
                                },
                                "inscriptionProtocol": "",
                            }
                            for code, description in BOARDS.items()
                        ],
                        "establishmentDate": day.isoformat(),
                    },
                    # The paging parameters are required, but the full list is returned.
                    "endIndex": 30,
                    "startIndex": 0,
                    "rowCount": 30,
                    "searchOrderItems": [
                        {
                            "columnIndex": 1,
                            "insertedIndexColumn": 1,
                            "dataField": "abiCode",
                            "descending": False,
                        }
                    ],
                }
            ),
        )
        response.raise_for_status()
        registers[day] = {
            str(record["abiCode"]).zfill(5): record
            for record in response.json()
            if record.get("abiCode")
        }
    return registers


def get_bics_by_tax_code():
    """Return the BICs of the active Italian entities in GLEIF's mapping by their tax code."""
    url = get_download_url()
    print(f"Using URL: {url}")
    mapping = {bic: lei for bic, lei in get_bic_lei_mapping(url).items() if bic[4:6] == "IT"}
    entities = get_entities(mapping.values())

    bics = defaultdict(list)
    for bic, lei in sorted(mapping.items()):
        entity = entities.get(lei)
        if entity and entity["status"] == "ACTIVE" and entity.get("registeredAs"):
            bics[entity["registeredAs"].lstrip("0")].append(bic)
    return bics


def preferred_bic(bics):
    # Connected BICs are preferred over test and passive ones, and head office BICs over branch
    # ones. The branch code XXX is dropped, like in the rest of the registry.
    bic = max(bics, key=lambda bic: (location_rank(bic), bic.endswith("XXX")))
    return bic.removesuffix("XXX")


def make_entry(bank_code, full_name, bic, status=BankStatus.ACTIVE):
    name, short_name = split_bank_name(full_name)
    entry = {
        "country_code": "IT",
        "primary": True,
        "bic": bic,
        "bank_code": bank_code,
        "name": name,
        "short_name": short_name or name,
    }
    if status != BankStatus.ACTIVE:
        entry["status"] = status
    return entry


def post(client, endpoint, payload, attempts=3):
    # The cessations take several hundred requests, and the server occasionally drops one.
    for attempt in range(attempts):
        try:
            response = client.post(f"{GIAVA_URL}api/{endpoint}", content=json.dumps(payload))
            response.raise_for_status()
            return response.json()
        except httpx2.TransportError:
            if attempt == attempts - 1:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def get_cessation(client, record):
    """Return the status and the successor's bank code of an institution that has ceased."""
    history = post(client, "getIntermediaryHistory", {"idIntermediary": record["idIntermediary"]})
    successors = [m[1] for event in history if (m := SUCCESSION.match(event["description"]))]
    if successors:
        return BankStatus.MERGED, successors[-1].zfill(5)

    details = post(client, "getLegalPersonDetails", record)
    causes = [
        board["cancellationCause"]["code"]
        for board in details["intermediaryBoards"]
        if board.get("cancellationCause")
    ]
    if causes and causes[-1] in CLOSING_CAUSES:
        return BankStatus.CLOSED, None
    return BankStatus.DELISTED, None


def get_tax_code(record):
    return (record.get("taxCode") or "").lstrip("0")


def resolve_successor(bank_code, ceased, active):
    """Follow the successors of a merged bank code to the bank code that is active today."""
    seen = {bank_code}
    while bank_code not in active:
        status, successor = ceased.get(bank_code, (None, None, None))[1:]
        if status != BankStatus.MERGED or successor in seen:
            return None
        bank_code = successor
        seen.add(bank_code)
    return bank_code


def process(previous):
    today = datetime.now(UTC).date()
    dates = [date(year, 1, 1) for year in range(FIRST_YEAR, today.year + 1)] + [today]
    with get_client() as client:
        registers = get_registers(client, dates)

        active = registers[today]
        if len(active) < MIN_RECORDS:
            raise ValueError(f"Only {len(active)} banks found, the register may have changed")

        # Banks that have ceased keep the record they had in the last register that lists them.
        last_records = {}
        for day in dates[:-1]:
            for bank_code, record in registers[day].items():
                if bank_code not in active:
                    last_records[bank_code] = record
        print(f"Getting the cessations of {len(last_records)} banks...")
        ceased = {
            bank_code: (record["name"].strip(), *get_cessation(client, record))
            for bank_code, record in last_records.items()
        }

    # Some institutions continued under a new bank code without the history naming it, e.g.
    # UniCredito Italiano (03135) as UniCredit (02008). The tax code identifies the legal entity, so
    # a code that has ceased without a successor is merged into the one active bank that has its
    # tax code.
    active_by_tax_code = defaultdict(list)
    for bank_code, record in active.items():
        if tax_code := get_tax_code(record):
            active_by_tax_code[tax_code].append(bank_code)
    for bank_code, (name, status, _) in ceased.items():
        candidates = active_by_tax_code.get(get_tax_code(last_records[bank_code]), [])
        if status != BankStatus.MERGED and len(candidates) == 1:
            ceased[bank_code] = (name, BankStatus.MERGED, candidates[0])

    # GLEIF provides the BICs of active banks. The previous registry is the fallback for banks
    # GLEIF can't match (e.g. Italian branches of foreign banks) and the only source for the BICs
    # of banks that have ceased.
    gleif_bics = get_bics_by_tax_code()
    previous_bics = {entry["bank_code"]: entry["bic"] for entry in previous if entry.get("bic")}

    registry = []
    sources = defaultdict(int)
    for bank_code, record in sorted(active.items()):
        name, tax_code = record["name"].strip(), get_tax_code(record)
        if tax_code in gleif_bics:
            bic, source = preferred_bic(gleif_bics[tax_code]), "GLEIF"
        elif bank_code in previous_bics:
            bic, source = previous_bics[bank_code], "previous registry"
        else:
            bic, source = "", "none"
        sources[source] += 1
        registry.append(make_entry(bank_code, name, bic))
    print("BICs of active banks by source:", dict(sources))

    # Merged banks get the name and BIC of the bank that services their code today, where their
    # successors lead to an active bank.
    by_code = {entry["bank_code"]: entry for entry in registry}
    statuses = defaultdict(int)
    for bank_code, (name, status, successor) in sorted(ceased.items()):
        entry = make_entry(bank_code, name, previous_bics.get(bank_code, ""), status)
        if status == BankStatus.MERGED:
            entry["successor_bank_code"] = successor
            if (current := resolve_successor(bank_code, ceased, active)) is not None:
                servicer = by_code[current]
                entry["legacy_name"] = entry["name"]
                # Where the registry knows no BIC of the successor, the code's own BIC is better
                # than none.
                entry.update(
                    name=servicer["name"],
                    short_name=servicer["short_name"],
                    bic=servicer["bic"] or entry["bic"],
                )
        statuses[status] += 1
        registry.append(entry)
    print("Banks that have ceased by status:", dict(statuses))
    return registry


if __name__ == "__main__":
    runtime_test_split_bank_name()

    # Codes that are in neither register are kept from the previous registry, which is read
    # before it is replaced.
    previous = load_previous(OUTPUT)
    data = merge(process(previous), previous)
    write_json(OUTPUT, data, indent=2)
