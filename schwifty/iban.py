from __future__ import annotations

import re
import string
from typing import Dict
from typing import Optional

from pycountry import countries
from pycountry.db import Data

from schwifty import common
from schwifty import exceptions
from schwifty import registry
from schwifty.bic import BIC
from schwifty.checksum import algorithms
from schwifty.checksum import InputType


_spec_to_re: Dict[str, str] = {"n": r"\d", "a": r"[A-Z]", "c": r"[A-Za-z0-9]", "e": r" "}

_alphabet: str = string.digits + string.ascii_uppercase


def _get_iban_spec(country_code: str) -> dict:
    try:
        spec = registry.get("iban")
        assert isinstance(spec, dict)
        return spec[country_code]
    except KeyError:
        raise exceptions.InvalidCountryCode(f"Unknown country-code '{country_code}'")


def numerify(string: str) -> int:
    return int("".join(str(_alphabet.index(c)) for c in string))


def code_length(spec: Dict, code_type: str) -> int:
    start, end = spec["positions"][code_type]
    return end - start


def add_bban_checksum(country_code: str, bban: str) -> str:
    if country_code in ["IT", "SM"]:
        # The IBAN of San Marino is covered by the Italian IBAN and uses the same checksum
        checksum = algorithms["IT:default"].compute(bban[1:])
        bban = checksum + bban[1:]
    elif country_code == "BE":
        # The Belgian BBAN format is XXXYYYYYYYZZ where:
        # - XXX: bank code
        # - YYYYYYY: account number
        # - ZZ: mod 97 remainder of XXYYYYYYY
        # The bban passed to this function has this format XXX00YYYYY
        bban = bban[:3] + bban[5:]
        checksum = algorithms["BE:default"].compute(bban)
        bban = bban + checksum
    elif country_code == "FR":
        checksum = algorithms["FR:default"].compute(bban)
        bban = bban[0:21] + checksum
    return bban


class IBAN(common.Base):
    """The IBAN object.

    Examples:

        You create a new IBAN object by supplying an IBAN code in text form. The IBAN
        is validated behind the scenes and you can then access all relevant components
        as properties::

            >>> iban = IBAN('DE89 3704 0044 0532 0130 00')
            >>> iban.account_code
            '0532013000'
            >>> iban.bank_code
            '37040044'
            >>> iban.country_code
            'DE'
            >>> iban.checksum_digits
            '89'


    Args:
        iban (str): The IBAN code.
        allow_invalid (bool): If set to `True` IBAN validation is skipped on instantiation.
        validate_bban (bool): If set to `True` also check the country specific checksum with then
                              BBAN.

    Raises:
        InvalidStructure: If the IBAN contains invalid characters or the BBAN does not match the
                          country specific format.
        InvalidChecksumDigits: If the IBAN's checksum is invalid.
        InvalidLength: If the length does not match the country specific specification.

    .. versionchanged:: 2021.05.1
        Added the `validate_bban` parameter that controls if the country specific checksum within
        the BBAN is also validated.
    """

    def __init__(self, iban: str, allow_invalid: bool = False, validate_bban: bool = False) -> None:
        super().__init__(iban)
        if self.checksum_digits == "??":
            self._code = self.country_code + self._calc_checksum_digits() + self.bban

        if not allow_invalid:
            self.validate(validate_bban)

    def _calc_checksum_digits(self) -> str:
        return "{:02d}".format(98 - (numerify(self.bban + self.country_code) * 100) % 97)

    @classmethod
    def generate(
        cls, country_code: str, bank_code: str, account_code: str, branch_code: str = ""
    ) -> IBAN:
        """Generate an IBAN from it's components.

        If the bank-code and/or account-number have less digits than required by their
        country specific representation, the respective component is padded with zeros.

        Examples:

            To generate an IBAN do the following::

                >>> bank_code = '37040044'
                >>> account_code = '532013000'
                >>> iban = IBAN.generate('DE', bank_code, account_code)
                >>> iban.formatted
                'DE89 3704 0044 0532 0130 00'

        Args:
            country_code (str): The ISO 3166 alpha-2 country code.
            bank_code (str): The country specific bank-code.
            account_code (str): The customer specific account-code.

        .. versionchanged:: 2020.08.3
            Added the `branch_code` parameter to allow the branch code (or sort code) to be
            specified independently.

        .. versionchanged:: 2021.05.2
            Added support for generating the country specific checksum of the BBAN for Belgian
            banks.
        """
        spec: Dict = _get_iban_spec(country_code)
        bank_code_length: int = code_length(spec, "bank_code")
        branch_code_length: int = code_length(spec, "branch_code")
        account_code_length: int = code_length(spec, "account_code")

        if len(bank_code) == bank_code_length + branch_code_length:
            bank_code, branch_code = bank_code[:bank_code_length], bank_code[bank_code_length:]

        if len(bank_code) > bank_code_length:
            raise exceptions.InvalidBankCode(f"Bank code exceeds maximum size {bank_code_length}")

        if len(branch_code) > branch_code_length:
            raise exceptions.InvalidBranchCode(
                f"Branch code exceeds maximum size {branch_code_length}"
            )

        if len(account_code) > account_code_length:
            raise exceptions.InvalidAccountCode(
                f"Account code exceeds maximum size {account_code_length}"
            )

        bban = "0" * spec["bban_length"]
        positions = spec["positions"]
        components = {
            "bank_code": bank_code,
            "branch_code": branch_code,
            "account_code": account_code,
        }
        for key, value in components.items():
            end = positions[key][1]
            start = end - len(value)
            bban = bban[:start] + value + bban[end:]

        bban = add_bban_checksum(country_code, bban)
        return cls(country_code + "??" + bban)

    def validate(self, validate_bban: bool = False) -> bool:
        """Validate the structural integrity of this IBAN.

        This function will verify the country specific format as well as the Luhn checksum in the
        3rd and 4th position of the IBAN. For some countries (currently Germany and Italy) it will
        also verify the correctness of the country specific checksum within the BBAN if the
        `validate_bban` parameter is set to `True`. For German banks it will pick the appropriate
        algorithm based on the bank code and verify that the account code has the correct checksum.

        Note:
            You have to use the `allow_invalid` paramter when constructing the :class:`IBAN`-object
            to circumvent the implicit validation.

        Raises:
            InvalidStructure: If the IBAN contains invalid characters or the BBAN does not match the
                              country specific format.
            InvalidChecksumDigits: If the IBAN's checksum is invalid.
            InvalidLength: If the length does not match the country specific specification.

        .. versionchanged:: 2021.05.1
            Added the `validate_bban` parameter that controls if the country specific checksum
            within the BBAN is also validated.
        """
        self._validate_characters()
        self._validate_length()
        self._validate_format()
        self._validate_iban_checksum()
        if validate_bban:
            self._validate_bban_checksum()
        return True

    def _validate_characters(self) -> None:
        if not re.match(r"[A-Z]{2}\d{2}[A-Z]*", self.compact):
            raise exceptions.InvalidStructure(f"Invalid characters in IBAN {self.compact}")

    def _validate_length(self) -> None:
        if self.spec["iban_length"] != self.length:
            raise exceptions.InvalidLength("Invalid IBAN length")

    def _validate_format(self) -> None:
        if not self.spec["regex"].match(self.bban):
            raise exceptions.InvalidStructure(
                "Invalid BBAN structure: '{}' doesn't match '{}''".format(
                    self.bban, self.spec["bban_spec"]
                )
            )

    def _validate_iban_checksum(self) -> None:
        if self.numeric % 97 != 1 or self._calc_checksum_digits() != self.checksum_digits:
            raise exceptions.InvalidChecksumDigits("Invalid checksum digits")

    def _validate_bban_checksum(self) -> None:
        bank = self.bank or {}
        algo_name = bank.get("checksum_algo", "default")
        algo = algorithms.get(f"{self.country_code}:{algo_name}")
        if algo is None:
            return
        if algo.accepts == InputType.ACCOUNT_CODE:
            value = self.account_code
        elif algo.accepts == InputType.BBAN:
            value = self.bban
        else:
            assert False, "Unsupported checksum algorithm input type"
        if not algo.validate(value):
            raise exceptions.InvalidBBANChecksum("Invalid BBAN checksum")

    @property
    def is_valid(self) -> bool:
        """bool: Indicate if this is a valid IBAN.

        Note:
            You have to use the `allow_invalid` paramter when constructing the :class:`IBAN`-object
            to circumvent the implicit validation.

        Examples:
            >>> IBAN('AB1234567890', allow_invalid=True).is_valid
            False

        .. versionadded:: 2020.08.1
        """
        try:
            return self.validate()
        except exceptions.SchwiftyException:
            return False

    @property
    def numeric(self) -> int:
        """int: A numeric represenation of the IBAN."""
        return numerify(self.bban + self.compact[:4])

    @property
    def formatted(self) -> str:
        """str: The IBAN formatted in blocks of 4 digits."""
        return " ".join(self.compact[i : i + 4] for i in range(0, len(self.compact), 4))

    @property
    def spec(self) -> Dict:
        """dict: The country specific IBAN specification."""
        return _get_iban_spec(self.country_code)

    @property
    def bic(self) -> Optional[BIC]:
        """BIC or None: The BIC associated to the IBAN´s bank-code.

        If the bank code is not available in Schwifty's registry ``None`` is returned.

        .. versionchanged:: 2020.08.1
            Returns ``None`` if no appropriate :class:`BIC` can be constructed.
        """
        try:
            return BIC.from_bank_code(self.country_code, self.bank_code or self.branch_code)
        except exceptions.SchwiftyException:
            return None

    @property
    def country(self) -> Optional[Data]:
        """Country: The country this IBAN is registered in."""
        return countries.get(alpha_2=self.country_code)

    def _get_code(self, code_type: str) -> str:
        start, end = self.spec["positions"][code_type]
        return self.bban[start:end]

    @property
    def bban(self) -> str:
        """str: The BBAN part of the IBAN."""
        return self._get_component(start=4)

    @property
    def country_code(self) -> str:
        """str: ISO 3166 alpha-2 country code."""
        return self._get_component(start=0, end=2)

    @property
    def checksum_digits(self) -> str:
        """str: Two digit checksum of the IBAN."""
        return self._get_component(start=2, end=4)

    @property
    def bank_code(self) -> str:
        """str: The country specific bank-code."""
        return self._get_code(code_type="bank_code")

    @property
    def branch_code(self) -> str:
        """str or None: The branch-code of the bank if available."""
        return self._get_code(code_type="branch_code")

    @property
    def account_code(self) -> str:
        """str: The customer specific account-code"""
        return self._get_code(code_type="account_code")

    @property
    def bank(self) -> Optional[dict]:
        bank_registry = registry.get("bank_code")
        assert isinstance(bank_registry, dict)
        return bank_registry.get((self.country_code, self.bank_code))

    @property
    def bank_name(self) -> Optional[str]:
        """Optional[str]: The name of the bank associated with the IBAN bank code.

        Examples:
            >>> IBAN('DE89370400440532013000').bank_name
            'Commerzbank'

        .. versionadded:: 2022.04.2
        """

        return None if self.bank is None else self.bank["name"]

    @property
    def bank_short_name(self) -> Optional[str]:
        """Optional[str]: The name of the bank associated with the IBAN bank code.

        Examples:
            >>> IBAN('DE89370400440532013000').bank_short_name
            'Commerzbank Köln'

        .. versionadded:: 2022.04.2
        """

        return None if self.bank is None else self.bank["short_name"]


def add_bban_regex(country: str, spec: Dict) -> Dict:
    bban_spec = spec["bban_spec"]
    spec_re = r"(\d+)(!)?([{}])".format("".join(_spec_to_re.keys()))

    def convert(match: re.Match) -> str:
        quantifier = ("{%s}" if match.group(2) else "{1,%s}") % match.group(1)
        return _spec_to_re[match.group(3)] + quantifier

    spec["regex"] = re.compile("^{}$".format(re.sub(spec_re, convert, bban_spec)))
    return spec


registry.manipulate("iban", add_bban_regex)
