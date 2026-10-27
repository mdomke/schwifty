"""Offline checks for registry download link selection."""

import importlib.util
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
    script = load_script("get_bank_registry_gb")
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


def test_gb_lei_lookup_batches_without_itertools_batched() -> None:
    """The GB generator must batch its LEI lookups on Python 3.11 as well.

    ``itertools.batched`` only exists from Python 3.12 on, so importing it made this script
    -- and this whole test module -- fail with an ``ImportError`` on Python 3.11, which
    schwifty supports.
    """
    script = load_script("get_bank_registry_gb")
    assert not hasattr(script, "batched")
    assert list(script.chunked("abcde", 2)) == [("a", "b"), ("c", "d"), ("e",)]

    leis = [f"LEI{i:07d}" for i in range(250)]
    requested = []

    def fake_get(url, **kwargs):
        requested.append(kwargs["params"]["filter[lei]"].split(","))
        return SimpleNamespace(json=lambda: {"data": []})

    with patch.object(script.httpx2, "get", side_effect=fake_get):
        assert script.get_legal_names(set(leis)) == {}
    assert [len(batch) for batch in requested] == [100, 100, 50]
    assert [lei for batch in requested for lei in batch] == sorted(leis)


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
    script = load_script("get_bank_registry_gb")
    assert [bic for bic in bics if script.is_primary(bic, bics)] == primary
