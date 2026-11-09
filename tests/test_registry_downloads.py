"""Offline checks for registry download link selection."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import patch

import pytest


pytest.importorskip("httpx2")
pytest.importorskip("bs4")


def load_script(name: str) -> ModuleType:
    path = Path(__file__).parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_bank_download_page():
    script = load_script("get_bank_registry_de")
    with (
        patch.object(script.httpx2, "get", return_value=SimpleNamespace(content=b"<html></html>")),
        pytest.raises(RuntimeError, match="download link not found on"),
    ):
        script.get_download_url()


def test_missing_bank_data_file():
    script = load_script("get_bank_registry_de")
    pages = [b'<a href="/download-bankleitzahlen">Download</a>', b"<html></html>"]
    with (
        patch.object(
            script.httpx2, "get", side_effect=[SimpleNamespace(content=page) for page in pages]
        ),
        pytest.raises(RuntimeError, match="bank data file link not found"),
    ):
        script.get_download_url()


def test_bank_data_url():
    script = load_script("get_bank_registry_de")
    pages = [
        b'<a href="/download-bankleitzahlen">Download</a>',
        b'<a href="/blz-aktuell-txt-data.txt">Data</a>',
    ]
    with patch.object(
        script.httpx2, "get", side_effect=[SimpleNamespace(content=page) for page in pages]
    ) as request:
        assert script.get_download_url() == "https://www.bundesbank.de/blz-aktuell-txt-data.txt"
    assert request.call_count == 2


def test_missing_iban_download():
    script = load_script("get_iban_registry")
    with (
        patch.object(script.httpx2, "get", return_value=SimpleNamespace(content=b"<html></html>")),
        pytest.raises(RuntimeError, match="IBAN Registry download link not found"),
    ):
        script.get_raw()


def test_iban_download_bytes():
    script = load_script("get_iban_registry")
    pages = [
        b'<a data-tracking-title="IBAN Registry (TXT)" href="/registry.txt">Data</a>',
        b"example\xe9\r\n",
    ]
    with patch.object(
        script.httpx2, "get", side_effect=[SimpleNamespace(content=page) for page in pages]
    ) as request:
        assert script.get_raw() == "example\u00e9\r\n"
    assert request.call_count == 2
    assert request.call_args.args[0] == "https://www.swift.com/registry.txt"


def test_gleif_download_url() -> None:
    script = load_script("gleif")
    files = {
        "data": [
            {
                "attributes": {
                    "uploadedAt": "2026-08-28T00:00:00Z",
                    "valid": True,
                    "downloadLink": "old",
                }
            },
            {
                "attributes": {
                    "uploadedAt": "2026-10-23T00:00:00Z",
                    "valid": False,
                    "downloadLink": "bad",
                }
            },
            {
                "attributes": {
                    "uploadedAt": "2026-09-25T00:00:00Z",
                    "valid": True,
                    "downloadLink": "new",
                }
            },
        ]
    }
    with patch.object(script.httpx2, "get", return_value=SimpleNamespace(json=lambda: files)):
        assert script.get_download_url() == "new"


@pytest.mark.parametrize(
    ("bics", "primary"),
    [
        (["PAYRGB21XXX", "PAYRGB2LXXX"], ["PAYRGB2LXXX"]),
        (["HLFXGB21XXX", "HLFXGB22XXX"], ["HLFXGB22XXX"]),
        (["MONZGB2LXXX"], ["MONZGB2LXXX"]),
        (["ABBYGB2LXXX", "ABBYGB3EXXX"], []),
    ],
)
def test_gleif_primary_bic(bics: list[str], primary: list[str]) -> None:
    script = load_script("gleif")
    assert [bic for bic in bics if script.is_primary(bic, bics)] == primary


def bundesbank_record(
    bank_code: str,
    name: str,
    bic: str,
    *,
    feature: str = "1",
    checksum: str = "06",
    deletion_flag: str = "0",
    successor: str = "00000000",
) -> dict[str, str]:
    return {
        "bank_code": bank_code,
        "feature": feature,
        "name": name,
        "short_name": name,
        "bic": bic,
        "check_digit_method": checksum,
        "deletion_flag": deletion_flag,
        "successor_bank_code": successor,
    }


def test_merged_bank_code_becomes_alias_of_successor() -> None:
    script = load_script("get_bank_registry_de")
    records = [
        bundesbank_record("10000001", "Volksbank", "GENODEF1AAA", checksum="32"),
        bundesbank_record(
            "10000002",
            "Volksbank Alt -alt-",
            "GENODEF1BBB",
            deletion_flag="1",
            successor="10000001",
        ),
        bundesbank_record(
            "10000002",
            "Volksbank Alt -alt- Gf",
            "GENODEF1BBC",
            feature="2",
            deletion_flag="1",
            successor="10000001",
        ),
    ]
    registry = script.process(records, [])
    assert [entry for entry in registry if entry["bank_code"] == "10000002"] == [
        {
            "bank_code": "10000002",
            "name": "Volksbank",
            "short_name": "Volksbank",
            "bic": "GENODEF1AAA",
            "primary": False,
            "country_code": "DE",
            "checksum_algo": "06",
            "status": "merged",
            "successor_bank_code": "10000001",
            "legacy_name": "Volksbank Alt",
            "legacy_bic": "GENODEF1BBB",
        }
    ]


def test_old_suffix_is_dropped_from_the_names_of_retired_banks() -> None:
    script = load_script("get_bank_registry_de")
    records = [
        bundesbank_record("10000001", "Volksbank", "GENODEF1AAA"),
        bundesbank_record("10000005", "Raiffeisenbank -alt-", "GENODEF1EEE"),
        bundesbank_record(
            "10000002",
            "Volksbank Alt -alt-",
            "GENODEF1BBB",
            deletion_flag="1",
            successor="10000001",
        ),
    ]
    previous = [
        {
            "bank_code": "10000003",
            "name": "Sparkasse  -alt-",
            "short_name": "Sparkasse-alt",
            "bic": "SPKADEFFXXX",
            "primary": True,
            "checksum_algo": "09",
        }
    ]
    registry = {entry["bank_code"]: entry for entry in script.process(records, previous)}
    # Bank codes that are still active keep the name the Bundesbank lists them with.
    assert registry["10000005"]["name"] == "Raiffeisenbank -alt-"
    assert registry["10000002"]["name"] == "Volksbank"
    assert registry["10000002"]["legacy_name"] == "Volksbank Alt"
    assert registry["10000003"]["name"] == "Sparkasse"
    assert registry["10000003"]["short_name"] == "Sparkasse"


def test_retired_bank_codes_are_kept() -> None:
    script = load_script("get_bank_registry_de")
    records = [bundesbank_record("10000001", "Volksbank Neu", "GENODEF1AAA")]
    previous = [
        {
            "bank_code": "10000001",
            "name": "Volksbank",
            "bic": "GENODEF1AAA",
            "primary": True,
            "checksum_algo": "06",
        },
        {
            "bank_code": "10000002",
            "name": "Volksbank",
            "bic": "GENODEF1AAA",
            "primary": False,
            "checksum_algo": "32",
            "status": "merged",
            "successor_bank_code": "10000001",
            "legacy_name": "Volksbank Alt",
            "legacy_bic": "GENODEF1BBB",
        },
        {
            "bank_code": "10000003",
            "name": "Closed Bank",
            "bic": "CLOSDEFFXXX",
            "primary": True,
            "checksum_algo": "09",
        },
        {"bank_code": "10000003", "name": "Closed Bank Gf", "bic": "CLOSDEFF001", "primary": False},
        # Closed banks are only kept if their account codes can still be validated.
        {"bank_code": "10000004", "name": "Old Bank", "bic": "OLDBDEFFXXX", "primary": True},
    ]
    registry = {
        (entry["bank_code"], entry["bic"]): entry for entry in script.process(records, previous)
    }
    assert set(registry) == {
        ("10000001", "GENODEF1AAA"),
        ("10000002", "GENODEF1AAA"),
        ("10000003", "CLOSDEFFXXX"),
    }
    # The current list wins, and aliases pick up changes of their successor.
    assert registry["10000001", "GENODEF1AAA"]["name"] == "Volksbank Neu"
    assert registry["10000002", "GENODEF1AAA"]["name"] == "Volksbank Neu"
    assert registry["10000002", "GENODEF1AAA"]["checksum_algo"] == "32"
    assert registry["10000002", "GENODEF1AAA"]["status"] == "merged"
    assert registry["10000002", "GENODEF1AAA"]["legacy_name"] == "Volksbank Alt"
    assert registry["10000002", "GENODEF1AAA"]["legacy_bic"] == "GENODEF1BBB"
    # The Bundesbank doesn't say why a code without a successor was deleted.
    assert registry["10000003", "CLOSDEFFXXX"] == {**previous[2], "status": "delisted"}


SCL_DIRECTORY = """Gueltig ab / valid from 02.11.2026;;;;;;
BIC;Name;SERVICE SCT;SERVICE COR;SERVICE COR1;SERVICE B2B;SERVICE SCC
AABAFI22;BANK OF ALAND PLC;1;0;1;0;0
ABRNIE21;PEOPLE FIRST CREDIT UNION;1;1;0;0;0
ABRNIE21XYZ;PEOPLE FIRST CREDIT UNION BRANCH;1;0;0;0;0
SPBAATWWXXX;SPARDA-BANK AUSTRIA;1;0;0;0;0
SPBAATWW;SPARDA-BANK AUSTRIA;1;1;0;1;0
"""


def test_scl_directory_is_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    script = load_script("get_scl_directory")
    monkeypatch.setattr(script, "MIN_RECORDS", 1)
    directory = script.parse(SCL_DIRECTORY)
    # COR1 was merged into the core direct debit.
    assert directory["AABAFI22"] == ("BANK OF ALAND PLC", ["COR", "SCT"])
    # Both forms of a BIC are the same BIC, so their schemes are combined.
    assert directory["SPBAATWW"] == ("SPARDA-BANK AUSTRIA", ["B2B", "COR", "SCT"])
    assert "SPBAATWWXXX" not in directory
    assert json.loads(script.dump(directory)) == {
        "AABAFI22": ["COR", "SCT"],
        "ABRNIE21": ["COR", "SCT"],
        "ABRNIE21XYZ": ["SCT"],
        "SPBAATWW": ["B2B", "COR", "SCT"],
    }


def test_scl_directory_rejects_a_changed_format() -> None:
    script = load_script("get_scl_directory")
    with pytest.raises(ValueError, match="Columns"):
        script.parse("valid from\nBIC;Name\nAABAFI22;BANK OF ALAND PLC\n")
    with pytest.raises(ValueError, match="Only"):
        script.parse(SCL_DIRECTORY)


def test_bank_registry_from_scl_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    script = load_script("get_scl_directory")
    monkeypatch.setattr(script, "MIN_RECORDS", 1)
    registry = script.bank_registry(script.parse(SCL_DIRECTORY), "IE")
    assert [(entry["bank_code"], entry["bic"], entry["primary"]) for entry in registry] == [
        ("ABRN", "ABRNIE21", True),
        ("ABRN", "ABRNIE21XYZ", False),
    ]
