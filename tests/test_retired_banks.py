from random import Random

import pytest

from schwifty import BBAN
from schwifty import BIC
from schwifty import IBAN
from schwifty import registry
from schwifty.exceptions import InvalidBankCode
from schwifty.exceptions import InvalidBBANChecksum


# Eurocity Bank was closed without a successor; its bank code uses checksum method 16.
CLOSED_BANK_CODE = "10030700"
CLOSED_BIC = "DLGHDEB1XXX"


def test_closed_bank_is_only_returned_on_request() -> None:
    iban = IBAN.generate("DE", bank_code=CLOSED_BANK_CODE, account_code="1234567890")
    assert iban.bank is None
    assert iban.bank_name is None
    assert iban.bic is None

    bank = iban.get_bank(include_closed=True)
    assert bank is not None
    assert bank.name == "Eurocity Bank"
    assert bank.retired is True
    assert bank.closed is True
    assert bank.successor_bank_code is None


def test_closed_bank_is_excluded_from_registry_lookups() -> None:
    assert registry.get_banks_by_code("DE", CLOSED_BANK_CODE) == []
    assert registry.get_banks_by_code("DE", CLOSED_BANK_CODE, include_closed=True)
    assert all(not bank.closed for bank in registry.get_all_banks())
    assert any(bank.closed for bank in registry.get_all_banks(include_closed=True))


def test_closed_bank_bic_lookups() -> None:
    with pytest.raises(InvalidBankCode):
        BIC.from_bank_code("DE", CLOSED_BANK_CODE)
    assert BIC.from_bank_code("DE", CLOSED_BANK_CODE, include_closed=True) == CLOSED_BIC
    assert BIC(CLOSED_BIC).exists is False
    assert BIC(CLOSED_BIC).bank_names == []


def test_account_codes_of_closed_banks_are_still_validated() -> None:
    bban = BBAN.random("DE", random=Random(0), bank_code=CLOSED_BANK_CODE)  # noqa: S311
    assert bban.validate_national_checksum() is True

    account_code = bban.account_code
    invalid = f"{account_code[:-1]}{(int(account_code[-1]) + 1) % 10}"
    with pytest.raises(InvalidBBANChecksum):
        BBAN("DE", f"{CLOSED_BANK_CODE}{invalid}").validate_national_checksum()


@pytest.mark.parametrize(
    ("country_code", "bank_code", "successor_bank_code", "name"),
    [
        ("DE", "13061088", "13061078", "Volks- und Raiffeisenbank"),
        ("CH", "31000", "30005", "UBS Switzerland AG - Zürich"),
        ("SI", "03100", "04000", "OTP BANKA D.D."),
    ],
)
def test_merged_bank_code_resolves_to_successor(
    country_code: str, bank_code: str, successor_bank_code: str, name: str
) -> None:
    bban = BBAN.from_components(country_code, bank_code=bank_code)
    bank = bban.bank
    assert bank is not None
    assert bank.retired is True
    assert bank.closed is False
    assert bank.successor_bank_code == successor_bank_code
    assert bank.name == name
    assert bban.bic == BBAN.from_components(country_code, bank_code=successor_bank_code).bic


def test_bic_of_merged_bank_resolves_to_its_retired_bank_code() -> None:
    # Raiffeisenbank Wismar (13061088) was merged into Volks- und Raiffeisenbank (13061078).
    bic = BIC("GENODEF1HWR")
    assert bic.exists is True
    assert bic.domestic_bank_codes == ["13061088"]
    assert bic.bank_names == ["Volks- und Raiffeisenbank"]

    (bank,) = registry.get_banks_by_bic("GENODEF1HWR")
    assert bank.legacy_bic == "GENODEF1HWR"
    assert bank.bic == "GENODEF1HWI"
    assert bank.successor_bank_code == "13061078"

    iban = IBAN.generate("DE", bank_code="13061088", account_code="1234567")
    assert iban.bic == "GENODEF1HWI"


def test_merged_bank_code_keeps_its_checksum_method() -> None:
    # Account codes issued under the retired bank code of Volksbank Wismar were computed with
    # its own method (06), not the one of its successor (32).
    (alias,) = registry.get_banks_by_code("DE", "13091084")
    (successor,) = (b for b in registry.get_banks_by_code("DE", "13061078") if b.primary)
    assert alias.successor_bank_code == successor.bank_code
    assert alias.checksum_algo == "06"
    assert successor.checksum_algo == "32"


def test_successors_of_retired_bank_codes_are_active() -> None:
    for bank in registry.get_all_banks():
        if bank.successor_bank_code is None:
            continue
        successors = registry.get_banks_by_code(bank.country_code, bank.successor_bank_code)
        assert successors, bank
        assert not any(successor.retired for successor in successors), bank


def test_random_never_uses_retired_bank_codes() -> None:
    for seed in range(300):
        for country_code in ("DE", "LV", "SI"):
            bank = IBAN.random(country_code, random=Random(seed)).bank  # noqa: S311
            assert bank is None or not bank.retired
