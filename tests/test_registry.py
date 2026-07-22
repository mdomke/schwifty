from schwifty import BIC
from schwifty import registry
from schwifty.checksum.poland import DefaultAlgorithm
from schwifty.domain import Component


def test_validate_bics():
    for bank in registry.get_all_banks():
        if bank.bic:
            BIC(bank.bic, allow_invalid=False)


def test_validate_cz_encoding():
    names = [bank.name for bank in registry.get_banks_by_country("CZ")]
    assert "Komerční banka, a.s." in names
    assert "Československá obchodní banka, a. s." in names


def test_valid_national_checksum_pl():
    algo = DefaultAlgorithm()
    for bank in registry.get_banks_by_country("PL"):
        bank_code = bank.bank_code
        check_digit = bank_code[7]
        branch_code = bank_code[3:7]
        bank_code = bank_code[:3]

        assert algo.compute([bank_code, branch_code]) == check_digit


def test_bank_code_matches_spec():
    for country_code in registry.get_countries():
        spec = registry.get_iban_spec(country_code)
        start, end = spec.bban_length, 0
        for component in spec.bic_lookup_components or [Component.BANK_CODE]:
            pos = spec.positions[component]
            start = min(start, pos.start)
            end = max(end, pos.end)
        length = end - start
        for bank in registry.get_banks_by_country(country_code):
            bank_code = bank.bank_code
            if not bank_code:
                continue
            assert len(bank_code) == length


def test_registry_domain_queries():
    countries = registry.get_countries()
    assert "DE" in countries
    assert "FR" in countries

    de_spec = registry.get_iban_spec("DE")
    assert de_spec.bban_length == 18
    assert de_spec.regex is not None

    de_banks = registry.get_banks_by_country("DE")
    assert len(de_banks) > 0

    commerzbank_code = "37040044"
    matching_banks = registry.get_banks_by_code("DE", commerzbank_code)
    assert len(matching_banks) > 0
    assert any(bank.name == "Commerzbank" for bank in matching_banks)

    matching_bic_banks = registry.get_banks_by_bic("DEUTDEDB200")
    assert len(matching_bic_banks) > 0
