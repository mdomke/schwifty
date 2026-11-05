#!/usr/bin/env python
from scripts.gleif import get_registry
from scripts.output import write_json
from scripts.retired import load_previous
from scripts.retired import merge


OUTPUT = "schwifty/bank_registry/generated_gb.json"
MIN_RECORDS = 1000


def process():
    registry = get_registry("GB")
    if len(registry) < MIN_RECORDS:
        raise ValueError(f"Only {len(registry)} records parsed, the mapping may have changed")
    return registry


if __name__ == "__main__":
    # GLEIF drops the BICs of entities that are no longer active from its mapping, so the previous
    # registry is the only source for their bank codes. Read it before replacing it.
    data = merge(process(), load_previous(OUTPUT))
    write_json(OUTPUT, data, indent=2)
