from schwifty import BIC
from schwifty import registry


def test_validate_bics():
    for bic in (bank["bic"] for bank in registry.get("bank") if bank["bic"]):
        BIC(bic, allow_invalid=False)
