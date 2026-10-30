import copy
import pickle
from contextlib import suppress
from random import Random

import pytest

from schwifty import IBAN
from schwifty import registry
from schwifty.bban import BBAN
from schwifty.domain import Bank
from schwifty.exceptions import GenerateRandomOverflowError
from schwifty.exceptions import InvalidAccountCode
from schwifty.exceptions import InvalidBBANChecksum
from schwifty.exceptions import NationalChecksumNotVerified
from schwifty.exceptions import SchwiftyException


def test_validate_national_checksum() -> None:
    # A valid national checksum returns True (consistent with the "no checksum
    # algorithm" case), while an invalid one raises InvalidBBANChecksum.
    assert BBAN("BE", "539007547034").validate_national_checksum() is True
    assert BBAN("GB", "WEST12345698765432").validate_national_checksum() is True
    with pytest.raises(InvalidBBANChecksum):
        BBAN("BE", "539007547035").validate_national_checksum()

    # Bosnia and Herzegovina (BA) uses ISO 7064 mod 97-10; it was previously
    # registered under the wrong country code "BT" (#264), so the national
    # checksum was never validated.
    assert BBAN("BA", "1290079401028494").validate_national_checksum() is True
    with pytest.raises(InvalidBBANChecksum):
        BBAN("BA", "1290079401028400").validate_national_checksum()


@pytest.mark.parametrize("country_code", ["HU", "SE"])
def test_validate_national_checksum_reports_a_missing_algorithm(country_code: str) -> None:
    # Both countries declare a national check-digit field (HU: 23-24, SE: 19-20) but have no
    # algorithm registered for it, so their check digits were accepted without being looked
    # at (#310). A missing algorithm must not reject an otherwise valid BBAN, but the pass is
    # no longer silent.
    iban = IBAN.random(country_code=country_code, random=Random(42), use_registry=False)  # noqa: S311
    with pytest.warns(NationalChecksumNotVerified, match=country_code):
        assert iban.bban.validate_national_checksum() is True
    with pytest.warns(NationalChecksumNotVerified, match=country_code):
        assert iban.validate(validate_bban=True) is True
    with pytest.warns(NationalChecksumNotVerified, match=country_code):
        IBAN(str(iban), validate_bban=True)


@pytest.mark.filterwarnings("error")
def test_validate_national_checksum_without_declared_check_digits_is_silent() -> None:
    # Countries that declare no national check digits have nothing to verify, so there is
    # nothing to report either.
    assert BBAN("GB", "WEST12345698765432").validate_national_checksum() is True


@pytest.mark.filterwarnings("error")
def test_random_does_not_report_an_unverifiable_national_checksum() -> None:
    # Generating a random BBAN is not a validation request: it neither reports a checksum it
    # cannot verify nor exhausts its retries over it.
    bban = BBAN.random("HU", random=Random(42))  # noqa: S311
    assert bban.country_code == "HU"


def test_validate_german_national_checksum() -> None:
    # The per-bank German checksum method is selected via the bank's
    # ``checksum_algo`` field. Commerzbank (bank code 37040044) uses method 13,
    # whose check digit sits at account position 8. A matching account validates;
    # a corrupted check digit raises. This path was silently skipped while
    # ``checksum_algo`` was dropped during registry deserialization.
    assert BBAN("DE", "370400440532013000").validate_national_checksum() is True
    with pytest.raises(InvalidBBANChecksum):
        BBAN("DE", "370400440532013100").validate_national_checksum()


def test_bank_prefers_the_primary_registry_record() -> None:
    # A national registry lists one record per branch, so a bank code maps to
    # several entries and ``primary`` marks the institution's main record.
    # ``BBAN.bank`` returned the first match in file order instead, which made
    # ``IBAN.bank``/``IBAN.bank_name`` describe a different institution than
    # ``IBAN.bic`` does: for the Nord LB codes the branch record is listed before
    # the institution's own record.
    iban = IBAN.generate("DE", "29050000", "0000000000")
    assert iban.bic == "BRLADE22XXX"
    assert iban.bank is not None
    assert iban.bank.bic == iban.bic
    assert iban.bank.primary is True
    assert iban.bank_short_name == "Nord LB Bremen"


def test_bank_prefers_the_primary_record_of_every_registered_bank_code() -> None:
    # Whenever the registry marks a record of a bank code as the primary one, that
    # is the record the bank code has to resolve to. ``BBAN.bank`` used to return
    # whichever entry happened to be read first.
    not_primary = []
    for country_code in registry.get_countries():
        for bank_code in sorted(
            {bank.bank_code for bank in registry.get_banks_by_country(country_code)}
        ):
            entries = registry.get_banks_by_code(country_code, bank_code)
            if not bank_code or not any(bank.primary for bank in entries):
                continue
            bban = BBAN.from_components(country_code, bank_code=bank_code)
            if bban.bank is not None and not bban.bank.primary:
                not_primary.append((country_code, bank_code, bban.bank.bic))
    assert not not_primary


@pytest.mark.parametrize(
    "bank_code",
    [
        "37040044",  # Commerzbank, method 13
        "30022000",  # NRW.BANK, method 08
        "10070000",  # Deutsche Bank, method 63
        "20030000",  # UniCredit Bank - HypoVereinsbank, method 68
        "10080000",  # Commerzbank vorm. Dresdner Bank, method 76
        "70090100",  # Hausbank München, method 88
        "10020890",  # UniCredit Bank - HypoVereinsbank, method 99
        "50010517",  # ING-DiBa, method C1
        "13051042",  # Sparkasse Vorpommern auf Rügen, method C0
        "35060386",  # Volksbank Rhein-Ruhr, method 40
        "25020600",  # Openbank Deutschland, method 41
        "66661454",  # VR Bank im Enzkreis -alt-, method 42
        "66690000",  # Volksbank Pforzheim -alt-, method 43
        "30060010",  # DZ BANK, method 44
        "50310400",  # Barclays Bank Ireland Frankfurt Branch, method 46
        "27290087",  # Volksbank Weserbergland -alt-, method 47
        "20190109",  # Volksbank Raiffeisenbank, method 48
        "20090700",  # Edekabank, method 50
    ],
)
def test_validate_national_checksum_on_truncated_bban(bank_code: str) -> None:
    # A BBAN that is too short to carry the 10-digit German account code has to be
    # rejected with InvalidAccountCode, no matter which method the bank uses. The
    # methods that inspect the account code before delegating to the shared length
    # check let a raw ValueError or IndexError escape instead.
    with pytest.raises(InvalidAccountCode):
        BBAN("DE", f"{bank_code}05320").validate_national_checksum()


def test_validate_national_checksum_of_every_german_bank_does_not_crash() -> None:
    # The same invariant across all methods the German registry refers to: a truncated
    # BBAN is either rejected with a schwifty exception or carries no national checksum
    # at all, but no raw ValueError or IndexError may escape.
    for bank in registry.get_banks_by_country("DE"):
        with suppress(SchwiftyException):
            BBAN("DE", f"{bank.bank_code}05320").validate_national_checksum()


def test_dict_access_is_deprecated() -> None:
    # ``IBAN.bank`` / ``IBAN.spec`` (and their BBAN counterparts) used to return
    # dicts; subscription and ``.get()`` are kept working for backward
    # compatibility but now emit a DeprecationWarning in favour of attribute
    # access.
    bban = BBAN("DE", "370400440532013000")
    bank = bban.bank
    assert bank is not None
    with pytest.deprecated_call():
        assert bank["name"] == bank.name
    with pytest.deprecated_call():
        assert bank.get("checksum_algo") == bank.checksum_algo
    with pytest.deprecated_call():
        assert bban.spec["bban_length"] == bban.spec.bban_length


@pytest.mark.parametrize("country_code", ["DE", "ES", "GB", "FR", "PL"])
def test_random(country_code: str) -> None:
    n = 100
    bbans = {BBAN.random(country_code) for _ in range(n)}
    assert len(bbans) == n

    for bban in bbans:
        assert bban.bank is not None
        assert bban.country_code == country_code

    assert any(
        bban.bank is None
        for bban in (BBAN.random(country_code, use_registry=False) for _ in range(n))
    )


def test_random_national_checksum_overflow(monkeypatch: pytest.MonkeyPatch) -> None:
    # When no generated candidate ever satisfies the national checksum, random()
    # exhausts its retries and raises GenerateRandomOverflowError rather than
    # returning a BBAN with an invalid checksum.
    def always_invalid(self: BBAN) -> bool:
        raise InvalidBBANChecksum

    monkeypatch.setattr(BBAN, "validate_national_checksum", always_invalid)

    # Pin the bank ``random`` picks to one whose checksum method schwifty
    # implements. The validator is only consulted for those, so letting the
    # choice stay random made this test flaky: 64 of the 4805 German records name
    # a method we don't implement (e.g. "B8" or "D8"), and for those there is
    # nothing to retry and no overflow to raise.
    deutsche_bank = registry.get_banks_by_code("DE", "10070000")
    assert [bank.checksum_algo for bank in deutsche_bank] == ["63"]

    def only_deutsche_bank(country_code: str) -> list[Bank]:
        return deutsche_bank

    monkeypatch.setattr(registry, "get_banks_by_country", only_deutsche_bank)

    with pytest.raises(GenerateRandomOverflowError):
        BBAN.random("DE")


@pytest.mark.parametrize("use_registry", [True, False])
@pytest.mark.parametrize(
    ("bank_code", "checksum_algo"),
    [
        ("10070000", "63"),  # Deutsche Bank
        ("10110600", "17"),  # Quirin Privatbank
        ("50010517", "C1"),  # ING-DiBa
        ("13051042", "C0"),  # Sparkasse Vorpommern auf Rügen
        ("35060386", "40"),  # Volksbank Rhein-Ruhr
        ("25020600", "41"),  # Openbank Deutschland
        ("66661454", "42"),  # VR Bank im Enzkreis -alt-
        ("66690000", "43"),  # Volksbank Pforzheim -alt-
        ("30060010", "44"),  # DZ BANK
        ("50310400", "46"),  # Barclays Bank Ireland Frankfurt Branch
        ("27290087", "47"),  # Volksbank Weserbergland -alt-
        ("20190109", "48"),  # Volksbank Raiffeisenbank
        ("20090700", "50"),  # Edekabank
    ],
)
def test_random_with_bank_code_uses_the_banks_checksum_method(
    bank_code: str, checksum_algo: str, use_registry: bool
) -> None:
    # The result is validated against the checksum method of the requested bank, so the
    # check digit has to be solved for that method too. random() used the method of a
    # randomly picked bank instead (or none at all without the registry), and for methods
    # that rarely accept such an account code it ran out of retries and raised
    # GenerateRandomOverflowError for several of these seeds.
    assert {bank.checksum_algo for bank in registry.get_banks_by_code("DE", bank_code)} == {
        checksum_algo
    }
    for seed in range(50):
        bban = BBAN.random(
            "DE",
            random=Random(seed),  # noqa: S311
            use_registry=use_registry,
            bank_code=bank_code,
        )
        assert bban.bank_code == bank_code
        assert bban.validate_national_checksum() is True


@pytest.mark.parametrize("use_registry", [True, False])
@pytest.mark.parametrize(
    ("country_code", "values", "lookup_key"),
    [
        # Cut to the eight digits of the bank code field, so the result belongs to
        # Deutsche Bank (method 63).
        ("DE", {"bank_code": "100700001"}, "10070000"),
        # Slovenian banks are looked up by bank and branch code together.
        ("SI", {"bank_code": "01", "branch_code": "000"}, "01000"),
    ],
)
def test_random_with_bank_code_looks_up_the_bank_like_validation(
    monkeypatch: pytest.MonkeyPatch,
    country_code: str,
    values: dict[str, str],
    lookup_key: str,
    use_registry: bool,
) -> None:
    # The check digit has to be solved for the bank the result is validated against, so
    # random() has to look the bank up with the same key validation uses later.
    lookups: list[str] = []
    get_banks_by_code = registry.get_banks_by_code

    def record_lookup(country_code: str, bank_code: str) -> list[Bank]:
        lookups.append(bank_code)
        return get_banks_by_code(country_code, bank_code)

    monkeypatch.setattr(registry, "get_banks_by_code", record_lookup)

    for seed in range(20):
        bban = BBAN.random(
            country_code,
            random=Random(seed),  # noqa: S311
            use_registry=use_registry,
            **values,
        )
        assert bban.bank is not None
        assert bban.validate_national_checksum() is True
    assert set(lookups) == {lookup_key}


def test_pickle_roundtrip() -> None:
    bban = BBAN("CH", "04835012345678009")
    for proto in range(pickle.HIGHEST_PROTOCOL + 1):
        restored = pickle.loads(pickle.dumps(bban, protocol=proto))
        assert restored == bban
        assert restored.country_code == bban.country_code


def test_deepcopy() -> None:
    bban = BBAN("CH", "04835012345678009")
    bban_copy = copy.deepcopy(bban)
    assert bban_copy == bban
    assert bban_copy.country_code == bban.country_code
    assert id(bban_copy) != id(bban)


@pytest.mark.parametrize("country_code", ["AO", "GW", "IR", "KM", "MG", "MZ"])
def test_random_countries_without_positions(country_code: str) -> None:
    # These registry entries define a BBAN regex but no component positions.
    # random() must fall back to generating from the regex instead of
    # degenerating to an all-zero BBAN through from_components().
    iban = IBAN.random(country_code=country_code, random=Random(42), use_registry=False)  # noqa: S311
    assert iban.is_valid
    assert str(iban.bban) != "0" * len(iban.bban)


def test_from_components_unsupported_country() -> None:
    # Without component positions a BBAN cannot be assembled from components.
    # This raises the explicit "not supported" error rather than the misleading
    # "Bank code exceeds maximum size 0".
    with pytest.raises(SchwiftyException, match="BBAN generation for AO not supported"):
        BBAN.from_components("AO", bank_code="1234", account_code="12345678901234567")
