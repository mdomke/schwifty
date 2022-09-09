import pytest
from pycountry import countries

from schwifty import BIC
from schwifty import exceptions


def test_bic():
    bic = BIC("GENODEM1GLS")
    assert bic.formatted == "GENO DE M1 GLS"
    assert bic.validate()


def test_bic_allow_invalid():
    bic = BIC("GENODXM1GLS", allow_invalid=True)
    assert bic
    assert bic.country_code == "DX"
    with pytest.raises(exceptions.InvalidCountryCode):
        bic.validate()


def test_bic_no_branch_code():
    bic = BIC("GENODEM1")
    assert bic.branch_code == ""
    assert bic.formatted == "GENO DE M1"


def test_bic_properties():
    bic = BIC("GENODEM1GLS")
    assert bic.length == len(bic) == 11
    assert bic.bank_code == "GENO"
    assert bic.country_code == "DE"
    assert bic.location_code == "M1"
    assert bic.branch_code == "GLS"
    assert bic.domestic_bank_codes == ["43060967", "43060988"]
    assert bic.bank_names == [
        "GLS Gemeinschaftsbank",
        "GLS Gemeinschaftsbank (GAA)",
    ]
    assert bic.bank_short_names == [
        "GLS Bank in Bochum (GAA)",
        "GLS Gemeinschaftsbk Bochum",
    ]
    assert bic.country == countries.get(alpha_2="DE")
    with pytest.warns(DeprecationWarning):
        assert bic.bank_name == "GLS Gemeinschaftsbank"
    with pytest.warns(DeprecationWarning):
        assert bic.bank_short_name == "GLS Bank in Bochum (GAA)"
    with pytest.warns(DeprecationWarning):
        assert bic.country_bank_code == "43060967"
    assert bic.exists
    assert bic.type == "passive"


def test_unknown_bic_properties():
    bic = BIC("ABNAJPJTXXX")
    assert bic.length == len(bic) == 11
    assert bic.bank_code == "ABNA"
    assert bic.country_code == "JP"
    assert bic.location_code == "JT"
    assert bic.branch_code == "XXX"
    assert bic.country_bank_code is None
    assert bic.domestic_bank_codes == []
    assert bic.bank_name is None
    assert bic.bank_names == []
    assert bic.bank_short_name is None
    assert bic.bank_short_names == []
    assert not bic.exists
    assert bic.type == "default"


@pytest.mark.parametrize(
    "code,type",
    [
        ("GENODEM0GLS", "testing"),
        ("GENODEM1GLS", "passive"),
        ("GENODEM2GLS", "reverse billing"),
        ("GENODEMMGLS", "default"),
    ],
)
def test_bic_type(code, type):
    bic = BIC(code)
    assert bic.type == type


@pytest.mark.parametrize(
    "code,exc",
    [
        ("AAAA", exceptions.InvalidLength),
        ("AAAADEM1GLSX", exceptions.InvalidLength),
        ("12ABDEM1GLS", exceptions.InvalidStructure),
        ("GENOD1M1GLS", exceptions.InvalidStructure),
        ("GENOXXM1GLS", exceptions.InvalidCountryCode),
    ],
)
def test_invalid_bic(code, exc):
    with pytest.raises(exc):
        BIC(code)


@pytest.mark.parametrize(
    "country,bank_code,bic",
    [
        ("AT", "36274", "RZTIAT22274"),
        ("BE", "002", "GEBABEBB"),
        ("CZ", "0600", "AGBACZPP"),
        ("ES", "0209", "BSABESBB"),
        ("FI", "101", "NDEAFIHH"),
        ("DE", "43060967", "GENODEM1GLS"),
        ("HU", "107", "CIBHHUHB"),
        ("HR", "2485003", "CROAHR2X"),
        ("LV", "RIKO", "RIKOLV2XXXX"),
        ("NL", "ADYB", "ADYBNL2A"),
        ("PL", "10100055", "NBPLPLPWXXX"),
        ("RO", "BPOS", "BPOSROBU"),
        ("SE", "500", "ESSESESS"),
        ("SI", "01050", "BSLJSI2XFNB"),
        ("SK", "0900", "GIBASKBX"),
    ],
)
def test_bic_from_bank_code(country, bank_code, bic):
    bic = BIC.from_bank_code(country, bank_code)
    assert bic.compact == bic


def test_bic_from_unknown_bank_code():
    with pytest.raises(exceptions.InvalidBankCode):
        BIC.from_bank_code("PO", "12345678")


def test_bic_is_from_primary_bank_code():
    bic = BIC.from_bank_code("DE", "20070024")
    assert bic.compact == "DEUTDEDBHAM"


def test_magic_methods():
    bic = BIC("GENODEM1GLS")
    assert bic == "GENODEM1GLS"
    assert bic == BIC("GENODEM1GLS")
    assert bic != BIC("GENODEMMXXX")
    assert bic != 12345
    assert bic < "GENODEM1GLT"

    assert str(bic) == "GENODEM1GLS"
    assert hash(bic) == hash("GENODEM1GLS")
    assert repr(bic) == "<BIC=GENODEM1GLS>"
