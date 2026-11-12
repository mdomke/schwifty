from random import Random

import pytest

from schwifty import BBAN
from schwifty import BIC
from schwifty import IBAN
from schwifty import registry
from schwifty.domain import BankStatus
from schwifty.exceptions import InvalidBBANChecksum


# The Bundesbank deleted the bank code of Eurocity Bank without a successor; it uses checksum
# method 16.
CLOSED_BANK_CODE = "10030700"
CLOSED_BIC = "DLGHDEB1"


def test_closed_bank_is_returned_with_its_status() -> None:
    # The bank of an IBAN is identified even if it no longer exists. Its status tells that no
    # payments can be made to it.
    iban = IBAN.generate("DE", bank_code=CLOSED_BANK_CODE, account_code="1234567890")
    bank = iban.bank
    assert bank is not None
    assert bank.name == "Eurocity Bank"
    assert bank.status is BankStatus.DELISTED
    assert bank.successor_bank_code is None
    assert iban.bank_name == "Eurocity Bank"
    assert iban.bic == CLOSED_BIC


def test_closed_bank_is_included_in_registry_lookups() -> None:
    assert registry.get_banks_by_code("DE", CLOSED_BANK_CODE)
    assert any(bank.status is BankStatus.DELISTED for bank in registry.get_all_banks())


def test_closed_bank_bic_lookups() -> None:
    assert BIC.from_bank_code("DE", CLOSED_BANK_CODE) == CLOSED_BIC
    assert BIC(CLOSED_BIC).exists is True
    assert "Eurocity Bank" in BIC(CLOSED_BIC).bank_names


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
        ("CZ", "6100", "5500", "Raiffeisenbank a.s."),
    ],
)
def test_merged_bank_code_resolves_to_successor(
    country_code: str, bank_code: str, successor_bank_code: str, name: str
) -> None:
    bban = BBAN.from_components(country_code, bank_code=bank_code)
    bank = bban.bank
    assert bank is not None
    assert bank.status is BankStatus.MERGED
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


@pytest.mark.parametrize(
    ("legacy_bic", "bank_code", "bic"),
    [
        ("EQBKCZPP", "6100", "RZBCCZPP"),  # Equa bank, merged into Raiffeisenbank
        ("ABANSI2X", "05100", "KBMASI2X"),  # Abanka, merged into OTP banka
        ("SKBASI2X", "03100", "KBMASI2X"),  # SKB banka, merged into OTP banka
    ],
)
def test_legacy_bic_resolves_to_merged_bank_code(legacy_bic: str, bank_code: str, bic: str) -> None:
    assert BIC(legacy_bic).exists is True
    assert bank_code in BIC(legacy_bic).domestic_bank_codes
    bank = BIC(legacy_bic).bank
    assert bank is not None
    assert bank.legacy_bic == legacy_bic
    assert bank.bic == bic


def test_merged_bank_code_keeps_its_checksum_method() -> None:
    # Account codes issued under the retired bank code of Volksbank Wismar were computed with
    # its own method (06), not the one of its successor (32).
    (alias,) = registry.get_banks_by_code("DE", "13091084")
    (successor,) = (b for b in registry.get_banks_by_code("DE", "13061078") if b.primary)
    assert alias.successor_bank_code == successor.bank_code
    assert alias.checksum_algo == "06"
    assert successor.checksum_algo == "32"


def test_successors_of_retired_bank_codes_are_known() -> None:
    # A successor can have merged itself since, e.g. Banca Popolare di Bergamo into UBI Banca and
    # UBI Banca into Intesa Sanpaolo, but the chain of successors has to end. Some sources name
    # successors they don't list themselves, so only the registries whose update scripts build
    # aliases of the successor are required to know it.
    for bank in registry.get_all_banks():
        current, seen = bank, {bank.bank_code}
        while current.successor_bank_code is not None:
            successors = registry.get_banks_by_code(
                current.country_code, current.successor_bank_code
            )
            assert successors or current.country_code not in ("CH", "DE", "SI"), current
            if not successors:
                break
            assert current.successor_bank_code not in seen, bank
            seen.add(current.successor_bank_code)
            current = successors[0]


def test_random_never_uses_retired_bank_codes() -> None:
    for seed in range(300):
        for country_code in ("DE", "LV", "SI"):
            bank = IBAN.random(country_code, random=Random(seed)).bank  # noqa: S311
            assert bank is None or bank.status is BankStatus.ACTIVE
