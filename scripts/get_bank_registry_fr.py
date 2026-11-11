#!/usr/bin/env python
"""Generate the French and Monegasque bank registries from REGAFI.

REGAFI, the register of the Autorité de contrôle prudentiel et de résolution (ACPR), lists every
authorized institution with its bank codes (codes interbancaires, CIB) and LEI, but no BICs. The
BICs are taken from GLEIF's BIC-to-LEI mapping, preferring the ones that the SCL directory of the
Deutsche Bundesbank lists as reachable for SEPA payments (see ``scripts/get_scl_directory.py``).
"""

import json
import re
import unicodedata
from collections import defaultdict

import httpx2

from schwifty.domain import canonical_bic
from scripts import get_scl_directory
from scripts.gleif import get_bic_lei_mapping
from scripts.gleif import get_download_url
from scripts.gleif import location_rank
from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


URL = "https://www.regafi.fr/api/explore/v2.1/catalog/datasets/prd-banque-entites/exports/json"
OUTPUTS = {
    "FR": "schwifty/bank_registry/generated_fr.json",
    "MC": "schwifty/bank_registry/generated_mc.json",
}
MIN_RECORDS = 700
# Holding companies have bank codes, but don't keep accounts.
HOLDINGS = {"Compagnie financière holding", "Compagnie holding d'investissement"}
# Countries whose institutions are listed by REGAFI, but whose IBANs use their own country code.
OWN_COUNTRY_CODE = {"MONACO": "MC"}


def get_entities():
    response = httpx2.get(URL, follow_redirects=True, timeout=600)
    response.raise_for_status()
    return response.json()


def get_bank_codes(entities):
    """Return the entity of every bank code, leaving out holding companies."""
    by_bank_code = {}
    for entity in entities:
        if set(entity["categorie"] or []) <= HOLDINGS:
            continue
        for cib in json.loads(entity["cib"] or "[]"):
            by_bank_code[cib["code"]] = entity
    if len(by_bank_code) < MIN_RECORDS:
        raise ValueError(f"Only {len(by_bank_code)} bank codes found, the format may have changed")
    return by_bank_code


def normalize(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().upper()
    name = re.sub(r"[^A-Z0-9 ]", " ", name)
    name = re.sub(r"\b(SA|S A|SAS|SCA|SE|SOCIETE ANONYME|SOCIETE|COOPERATIVE|BANQUE)\b", " ", name)
    return " ".join(name.split())


def names(entity):
    yield entity["denomination"]
    yield from json.loads(entity["nom_commerciaux"] or "{}")
    if entity["sigle"]:
        yield entity["sigle"]


def preference(bic):
    # French BICs before foreign ones, the BIC of the primary office before branch BICs.
    return bic[4:6] != "FR", len(bic) != 8, bic


class BICSelector:
    """Choose the BIC of a bank code.

    The order of preference is:

    1. the entity's own BIC from GLEIF, if the SCL directory lists it or its institution as
       reachable, like ``BIC.sepa_schemes`` does. If several are, the one of the previous
       registry (or the manual one), which may have been curated, then the ones the directory
       lists themselves,
    2. the BIC of the previous registry,
    3. any other of the entity's BICs from GLEIF, connected ones before passive ones,
    4. a BIC of the SCL directory whose name matches the entity, and no other one.

    Passive BICs identify their institution just as well, and they can be reached through a
    correspondent. Whether a BIC can be reached for SEPA payments is told by its SEPA schemes.
    """

    def __init__(self, entities, bics_by_lei, scl, known):
        self.bics_by_lei = bics_by_lei
        self.scl = scl
        self.known = known
        claimed = {bic for bics in bics_by_lei.values() for bic in bics}
        candidates = defaultdict(set)
        by_name = defaultdict(set)
        for entity in entities:
            for name in names(entity):
                by_name[normalize(name)].add(entity["id_referentiel"])
        for bic, (name, _) in scl.items():
            if bic[4:6] in ("FR", "MC") and bic not in claimed and bic[:8] not in claimed:
                for entity_id in by_name.get(normalize(name), ()):
                    candidates[entity_id].add(bic)
        # A name match is only trusted if the BIC matches a single entity.
        owners = defaultdict(set)
        for entity_id, bics in candidates.items():
            for bic in bics:
                owners[bic].add(entity_id)
        self.by_name = {
            entity_id: sorted(bic for bic in bics if len(owners[bic]) == 1)
            for entity_id, bics in candidates.items()
        }

    def select(self, bank_code, entity):
        bics = self.bics_by_lei.get(entity["lei"] or "", [])
        reachable = [bic for bic in bics if bic in self.scl or bic[:8] in self.scl]
        if reachable:
            if self.known.get(bank_code) in reachable:
                return self.known[bank_code], "SCL directory"
            return min(
                reachable, key=lambda bic: (bic not in self.scl, *preference(bic))
            ), "SCL directory"
        if bank_code in self.known:
            return self.known[bank_code], "previous registry"
        if bics:
            return min(bics, key=lambda bic: (-location_rank(bic), *preference(bic))), "GLEIF"
        if matches := self.by_name.get(entity["id_referentiel"]):
            return min(matches, key=preference), "name"
        return "", "none"


def known_bics(*registries):
    """Return the BIC of the primary record of every bank code in ``registries``."""
    known = {}
    for registry in registries:
        records = defaultdict(list)
        for entry in registry:
            if entry.get("bic"):
                records[entry["bank_code"]].append(entry)
        for bank_code, entries in records.items():
            if bank_code not in known:
                best = min(entries, key=lambda e: (not e.get("primary"), *preference(e["bic"])))
                known[bank_code] = canonical_bic(best["bic"])
    return known


def process(entities, bics_by_lei, scl, known):
    bank_codes = get_bank_codes(entities)
    selector = BICSelector(entities, bics_by_lei, scl, known)
    registries = defaultdict(list)
    sources = defaultdict(int)
    for bank_code, entity in sorted(bank_codes.items()):
        bic, source = selector.select(bank_code, entity)
        sources[source] += 1
        country_code = OWN_COUNTRY_CODE.get(entity["pays"], "FR")
        registries[country_code].append(
            {
                "country_code": country_code,
                "primary": True,
                "bic": bic,
                "bank_code": bank_code,
                "name": entity["denomination"],
                "short_name": entity["denomination"],
            }
        )
    print("BICs by source:", dict(sources))
    return registries


def get_bics_by_lei():
    bics_by_lei = defaultdict(list)
    for bic, lei in get_bic_lei_mapping(get_download_url()).items():
        bics_by_lei[lei].append(canonical_bic(bic))
    return bics_by_lei


if __name__ == "__main__":
    # The previous registries are the only source for bank codes that REGAFI no longer lists, and
    # for curated BICs. Read them before replacing them.
    previous = {country_code: load_previous(path) for country_code, path in OUTPUTS.items()}
    manual = {
        country_code: load_previous(f"schwifty/bank_registry/manual_{country_code.lower()}.json")
        for country_code in OUTPUTS
    }
    known = known_bics(*previous.values(), *manual.values())
    scl = get_scl_directory.parse(get_scl_directory.get_raw())
    registries = process(get_entities(), get_bics_by_lei(), scl, known)
    for country_code, path in OUTPUTS.items():
        write_json(path, merge(registries[country_code], previous[country_code]), indent=2)
