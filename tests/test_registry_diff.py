"""Offline checks for the registry update tooling in ``scripts/``."""

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import registry_diff
from scripts import update
from scripts.registry_diff import compare
from scripts.registry_diff import render_markdown
from scripts.registry_diff import render_text


BANK_FILE = "schwifty/bank_registry/generated_de.json"
SCL_FILE = "schwifty/scl_registry/generated.json"
IBAN_FILE = "schwifty/iban_registry/generated.json"


def bank(code: str, name: str = "Bank", **fields: Any) -> dict[str, Any]:
    return {
        "country_code": "DE",
        "bank_code": code,
        "bic": "MARKDEF1100",
        "name": name,
        "short_name": name,
        "primary": True,
        **fields,
    }


def banks(count: int) -> list[dict[str, Any]]:
    return [bank(f"{100 + i:08d}") for i in range(count)]


def dump(data: Any) -> bytes:
    return json.dumps(data).encode()


def test_unchanged_file_has_no_changes() -> None:
    data = dump(banks(3))
    assert not compare(BANK_FILE, data, data).changed


def test_bank_changes() -> None:
    old = [
        bank("00000001", "Old Name"),
        bank("00000002"),
        bank("00000003", checksum_algo="00"),
        bank("00000004", bic="COBADEFFXXX"),
        bank("00000005", status="delisted"),
    ]
    new = [
        bank("00000001", "New Name"),
        bank("00000002", status="merged"),
        bank("00000003", checksum_algo="06"),
        bank("00000004", bic="DEUTDEFFXXX"),
        bank("00000005"),
        bank("00000006", "Added Bank"),
    ]
    report = compare(BANK_FILE, dump(old), dump(new))
    assert report.changes == {
        "Added": ["`00000006` Added Bank"],
        "Retired": ["`00000002` Bank (merged)"],
        "Reactivated": ["`00000005` Bank"],
        "Renamed": ["`00000001` Old Name → New Name"],
        "BIC changed": ["`00000004` COBADEFFXXX → DEUTDEFFXXX"],
        "Checksum method changed": ["`00000003` Bank: 00 → 06"],
    }
    assert report.problems == []
    assert report.warnings == []


def test_reads_v2_registries() -> None:
    old: dict[str, Any] = {"expand_from": "bank_codes", "expand_into": "bank_code", "entries": []}
    new = {**old, "entries": [{**bank(""), "bank_codes": ["00000001", "00000002"]}]}
    report = compare("schwifty/bank_registry/generated_at.v2.json", dump(old), dump(new))
    assert report.changes == {"Added": ["`00000001` Bank", "`00000002` Bank"]}


def test_small_registries_may_lose_a_few_banks() -> None:
    old = banks(10)
    new = [*old[:5], *(bank(entry["bank_code"], status="delisted") for entry in old[5:])]
    assert compare(BANK_FILE, dump(old), dump(new)).problems == []


def test_mass_retirement_is_a_problem() -> None:
    old = banks(200)
    new = [*old[:189], *(bank(entry["bank_code"], status="delisted") for entry in old[189:])]
    report = compare(BANK_FILE, dump(old), dump(new))
    assert report.problems == [
        "11 of 200 active bank codes were retired or dropped, more than the 10 allowed in one "
        "update. The source may be incomplete."
    ]


def test_dropped_bank_codes_count_as_removed() -> None:
    old = banks(10)
    report = compare(BANK_FILE, dump(old), dump(old[:4]))
    assert len(report.changes["Dropped"]) == 6
    assert len(report.problems) == 1
    assert report.warnings == ["6 bank codes were dropped instead of being kept as retired"]


@pytest.mark.parametrize(
    ("entry", "problem"),
    [
        (bank(""), "Missing bank code"),
        (bank("00000009", name=""), "`00000009` has no name"),
        (bank("00000009", bic="N/A"), "`00000009` has the invalid BIC 'N/A'"),
        (bank("00000009", country_code="de"), "`00000009` has the invalid country code 'de'"),
    ],
)
def test_invalid_entries_are_a_problem(entry: dict[str, Any], problem: str) -> None:
    report = compare(BANK_FILE, dump(banks(3)), dump([*banks(3), entry]))
    assert report.problems == ["1 invalid entries"]
    assert report.changes["Invalid"][0].startswith(problem)


def test_unimplemented_checksum_method_is_a_warning() -> None:
    new = [*banks(3), bank("00000009", checksum_algo="ZZ")]
    report = compare(BANK_FILE, dump(banks(3)), dump(new))
    assert report.problems == []
    assert report.warnings == [
        "Checksum method `ZZ` is not implemented, so account codes of 1 bank codes are not "
        "checked: 00000009"
    ]


def test_invalid_json_and_deleted_files_are_problems() -> None:
    assert compare(BANK_FILE, dump([]), b"[").problems[0].startswith("The file is not valid JSON")
    assert compare(BANK_FILE, dump([]), None).problems == ["The file was deleted"]


def test_new_file() -> None:
    report = compare(BANK_FILE, None, dump(banks(2)))
    assert len(report.changes["Added"]) == 2
    assert report.problems == []


def test_scl_changes() -> None:
    old = {f"BANKDEF{i}": ["SCT"] for i in range(10)}
    new = {**old, "BANKDEF0": ["COR", "SCT"], "NEWBDEFF": ["SCT"]}
    del new["BANKDEF9"]
    report = compare(SCL_FILE, dump(old), dump(new))
    assert report.changes == {
        "Added": ["`NEWBDEFF` SCT"],
        "Removed": ["`BANKDEF9`"],
        "Schemes changed": ["`BANKDEF0` SCT → COR, SCT"],
    }
    assert report.problems == []
    many_removed = {bic: old[bic] for bic in list(old)[:4]}
    assert compare(SCL_FILE, dump(old), dump(many_removed)).problems


def test_iban_changes() -> None:
    old = {"AD": {"bban_length": 20}, "AE": {"bban_length": 19}}
    report = compare(IBAN_FILE, dump(old), dump({"AD": {"bban_length": 21}, "YE": {}}))
    assert report.changes == {"Added": ["YE"], "Removed": ["AE"], "Changed": ["AD"]}
    assert report.problems == ["Countries were removed: AE"]


def test_render() -> None:
    old = banks(100)
    new = [bank(entry["bank_code"], f"Renamed {i}") for i, entry in enumerate(old)]
    reports = [compare(BANK_FILE, dump(old), dump(new))]
    text = render_text(reports)
    assert "Renamed: 100" in text
    assert "… and 75 more" in text
    markdown = render_markdown(reports)
    assert "| `bank_registry/generated_de.json` | 100 renamed | - | - |" in markdown
    assert len(render_markdown(reports, max_length=1000)) <= 1000
    assert render_text([]) == "No registry changes"
    assert render_markdown([]) == "No registry changes."


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(registry_diff, "ROOT", tmp_path)
    monkeypatch.setattr(update, "ROOT", tmp_path)
    (tmp_path / "schwifty" / "bank_registry").mkdir(parents=True)
    (tmp_path / BANK_FILE).write_bytes(dump(banks(10)))
    return tmp_path


def fake_source(root: Path, monkeypatch: pytest.MonkeyPatch, data: Any, exit_code: int = 0) -> None:
    script = f"from pathlib import Path\nPath({BANK_FILE!r}).write_text({json.dumps(data)!r})\n"
    (root / "fake_source.py").write_text(f"{script}raise SystemExit({exit_code})\n")
    monkeypatch.setattr(update, "SOURCES", {"fake": "fake_source"})


def test_update_keeps_good_changes(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_source(root, monkeypatch, [*banks(10), bank("00000001", "Added")])
    assert update.update("fake")
    assert len(json.loads((root / BANK_FILE).read_text())) == 11


@pytest.mark.parametrize(("data", "exit_code"), [(banks(10)[:3], 0), ([*banks(10), bank("1")], 1)])
def test_update_reverts_failures(
    root: Path, monkeypatch: pytest.MonkeyPatch, data: Any, exit_code: int
) -> None:
    before = (root / BANK_FILE).read_bytes()
    fake_source(root, monkeypatch, data, exit_code)
    assert not update.update("fake")
    assert (root / BANK_FILE).read_bytes() == before


def test_update_force_keeps_problems(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_source(root, monkeypatch, banks(10)[:3])
    assert update.update("fake", force=True)
    assert len(json.loads((root / BANK_FILE).read_text())) == 3


def test_renamed_branches_only_show_the_changed_names() -> None:
    old = [bank("00000001", f"Branch {i}") for i in range(100)]
    new = [*old[1:], bank("00000001", "Branch New " + "x" * 100)]
    report = compare(BANK_FILE, dump(old), dump(new))
    assert report.changes["Renamed"] == [f"`00000001` Branch 0 → Branch New {'x' * 68}…"]
    many = [bank("00000001", f"Other {i}") for i in range(5)]
    report = compare(BANK_FILE, dump(old[:5]), dump(many))
    assert report.changes["Renamed"] == [
        "`00000001` Branch 0, Branch 1, Branch 2, 2 more → Other 0, Other 1, Other 2, 2 more"
    ]
