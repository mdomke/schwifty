from __future__ import annotations

import re
import warnings
from typing import Any
from typing import TYPE_CHECKING

import iso3166
from pycountry import countries  # type: ignore
from pycountry.db import Data  # type: ignore

from schwifty import common
from schwifty import exceptions
from schwifty import registry


if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler
    from pydantic_core import CoreSchema

_bic_re = re.compile(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?")


class BIC(common.Base):
    """The BIC object.

    Examples:

        You can either create a new BIC object by providing a code as text::

            >>> bic = BIC('GENODEM1GLS')
            >>> bic.country_code
            'DE'
            >>> bic.location_code
            'M1'
            >>> bic.bank_code
            'GENO'

        or by using the :meth:`from_bank_code` classmethod::

            >>> bic = BIC.from_bank_code('DE', '43060967')
            >>> bic.formatted
            'GENO DE M1 GLS'

    Args:
        bic (str): The BIC number.
        allow_invalid (bool): If set to ``True`` validation is skipped on instantiation.

    Raises:
        InvalidLength: If the BIC's length is not 8 or 11 characters long.
        InvalidStructure: If the BIC contains unexpected characters.
        InvalidCountryCode: If the BIC's country code is unknown.

    .. versionchanged:: 2023.10.0
        The :class:`.BIC` is now a subclass of :class:`str` and supports all its methods.
    """

    def __init__(self, bic: str, allow_invalid: bool = False) -> None:
        super().__init__()
        if not allow_invalid:
            self.validate()

    @classmethod
    def candidates_from_bank_code(cls, country_code: str, bank_code: str) -> list[BIC]:
        """Create a list of potential BIC objects from country-code and domestic bank-code.

        Examples:
            >>> bic_codes = BIC.candidates_from_bank_code("FR", "30004")
            >>> bic_codes # doctest: +NORMALIZE_WHITESPACE
            [<BIC=BNPAFRPPIFN>, <BIC=BNPAFRPPPAA>, <BIC=BNPAFRPPMED>, \
             <BIC=BNPAFRPPCRN>, <BIC=BNPAFRPP>, <BIC=BNPAFRPPPAE>, <BIC=BNPAFRPPPBQ>,
             <BIC=BNPAFRPPNFE>, <BIC=BNPAFRPPPGN>, <BIC=BNPAFRPPXXX>, <BIC=BNPAFRPPBOR>,
             <BIC=BNPAFRPPCRM>, <BIC=BNPAFRPPPVD>, <BIC=BNPAFRPPPTX>, <BIC=BNPAFRPPPAC>,
             <BIC=BNPAFRPPPLZ>, <BIC=BNPAFRPP039>, <BIC=BNPAFRPPENG>, <BIC=BNPAFRPPNEU>,
             <BIC=BNPAFRPPORE>, <BIC=BNPAFRPPPEE>, <BIC=BNPAFRPPPXV>, <BIC=BNPAFRPPIFO>]

            >>> BIC.candidates_from_bank_code("DE", "20070024")
            [<BIC=DEUTDEDBHAM>]

            >>> BIC.candidates_from_bank_code("DE", "01010101")
            Traceback (most recent call last):
            ...
            InvalidBankCode: Unknown bank code '01010101' for country 'DE'


        Args:
            country_code (str): ISO 3166 alpha2 country-code.
            bank_code (str): Country specific bank-code.

        Returns:
            list[BIC]: a list of BIC objects generated from the given country code and bank code.

        Raises:
            InvalidBankCode: If the given bank code wasn't found in the registry

        Note:
            This currently only works for selected countries. Amongst them

            * Austria
            * Belgium
            * Bulgaria
            * Croatia
            * Czech Republic
            * Finland
            * France
            * Germany
            * Great Britan
            * Hungary
            * Ireland
            * Latvia
            * Lithuania
            * Netherlands
            * Poland
            * Romania
            * Saudi Arabia
            * Slovakia
            * Slovenia
            * Spain
            * Sweden
            * Switzerland
        """
        try:
            spec = registry.get("bank_code")
            assert isinstance(spec, dict)
            return [cls(entry["bic"]) for entry in spec[(country_code, bank_code)]]
        except KeyError as e:
            raise exceptions.InvalidBankCode(
                f"Unknown bank code {bank_code!r} for country {country_code!r}"
            ) from e

    @classmethod
    def from_bank_code(cls, country_code: str, bank_code: str) -> BIC:
        """Create a new BIC object from country-code and domestic bank-code.

        Examples:
            >>> bic = BIC.from_bank_code('DE', '20070000')
            >>> bic.country_code
            'DE'
            >>> bic.bank_code
            'DEUT'
            >>> bic.location_code
            'HH'

            >>> BIC.from_bank_code('DE', '01010101')
            Traceback (most recent call last):
            ...
            InvalidBankCode: Unknown bank code '01010101' for country 'DE'


        Args:
            country_code (str): ISO 3166 alpha2 country-code.
            bank_code (str): Country specific bank-code.

        Returns:
            BIC: a BIC object generated from the given country code and bank code.

        Raises:
            InvalidBankCode: If the given bank code wasn't found in the registry

        Note:
            This currently only works for selected countries. Amongst them

            * Austria
            * Belgium
            * Bulgaria
            * Croatia
            * Czech Republic
            * Finland
            * France
            * Germany
            * Great Britan
            * Hungary
            * Ireland
            * Latvia
            * Lithuania
            * Netherlands
            * Poland
            * Romania
            * Saudi Arabia
            * Slovakia
            * Slovenia
            * Spain
            * Sweden
            * Switzerland
        """
        try:
            candidates = cls.candidates_from_bank_code(country_code, bank_code)
            if len(candidates) > 1:
                # If we have multiple candidates, we try to pick the
                # one with no branch code which is the most generic one.
                generic_codes = [c for c in candidates if not c.branch_code]
                if generic_codes:
                    return sorted(generic_codes)[-1]

                # If we don't have one, we try to pick the one with
                # 'XXX' as a branch code
                generic_codes = [c for c in candidates if c.branch_code == "XXX"]
                if generic_codes:
                    return sorted(generic_codes)[-1]
            return candidates[0]
        except KeyError as e:
            raise exceptions.InvalidBankCode(
                f"Unknown bank code {bank_code!r} for country {country_code!r}"
            ) from e

    def validate(self) -> bool:
        """Validate the structural integrity of this BIC.

        This function will verify the correct length, structure and the existence of the country
        code.

        Note:
            You have to use the `allow_invalid` paramter when constructing the :class:`BIC`-object
            to circumvent the implicit validation.

        Raises:
            InvalidLength: If the BIC's length is not 8 or 11 characters long.
            InvalidStructure: If the BIC contains unexpected characters.
            InvalidCountryCode: If the BIC's country code is unknown.
        """
        self._validate_length()
        self._validate_structure()
        self._validate_country_code()
        return True

    def _validate_length(self) -> None:
        if len(self) not in (8, 11):
            raise exceptions.InvalidLength(f"Invalid length '{len(self)}'")

    def _validate_structure(self) -> None:
        if not _bic_re.match(str(self)):
            raise exceptions.InvalidStructure(f"Invalid structure '{self!s}'")

    def _validate_country_code(self) -> None:
        country_code = self.country_code
        try:
            iso3166.countries_by_alpha2[country_code]
        except KeyError as e:
            raise exceptions.InvalidCountryCode(f"Invalid country code '{country_code}'") from e

    @property
    def is_valid(self) -> bool:
        """bool: Indicate if this is a valid BIC.

        Note:
            You have to use the `allow_invalid` paramter when constructing the :class:`BIC`-object
            to circumvent the implicit validation.

        Examples:
            >>> BIC('FOOBARBAZ', allow_invalid=True).is_valid
            False

        .. versionadded:: 2020.08.1
        """
        try:
            return self.validate()
        except exceptions.SchwiftyException:
            return False

    @property
    def formatted(self) -> str:
        """str: The BIC separated in the blocks bank-, country- and location-code.

        Examples:
            >>> BIC('MARKDEF1100').formatted
            'MARK DE F1 100'
        """
        formatted = " ".join([self.bank_code, self.country_code, self.location_code])
        if self.branch_code:
            formatted += " " + self.branch_code
        return formatted

    def _lookup_values(self, key: str) -> list:
        spec = registry.get("bic")
        assert isinstance(spec, dict)
        entries = spec.get(str(self), [])
        return sorted({entry[key] for entry in entries})

    @property
    def domestic_bank_codes(self) -> list[str]:
        """List[str]: The country specific bank-codes associated with the BIC.

        Examples:
            >>> BIC('MARKDEF1100').domestic_bank_codes
            ['10000000']

        .. versionadded:: 2020.01.0
        """
        return self._lookup_values("bank_code")

    @property
    def bank_names(self) -> list[str]:
        """List[str]: The name of the banks associated with the BIC.

        Examples:
            >>> BIC('MARKDEF1100').bank_names
            ['Bundesbank']

        .. versionadded:: 2020.01.0
        """
        return self._lookup_values("name")

    @property
    def bank_short_names(self) -> list[str]:
        """List[str]: The short name of the banks associated with the BIC.

        Examples:
            >>> BIC('MARKDEF1100').bank_short_names
            ['BBk Berlin']

        .. versionadded:: 2020.01.0
        """
        return self._lookup_values("short_name")

    @property
    def country_bank_code(self) -> str | None:
        """str or None: The country specific bank-code associated with the BIC.

        .. deprecated:: 2020.01.0
           Use :meth:`domestic_bank_codes` instead.
        """
        warnings.warn("Use `BIC.domestic_bank_codes` instead", DeprecationWarning, stacklevel=2)
        codes = self.domestic_bank_codes
        return codes[0] if codes else None

    @property
    def bank_name(self) -> str | None:
        """str or None: The name of the bank associated with the BIC.

        .. deprecated:: 2020.01.0
           Use :meth:`bank_names` instead.
        """
        warnings.warn("Use `BIC.bank_names` instead", DeprecationWarning, stacklevel=2)
        names = self.bank_names
        return names[0] if names else None

    @property
    def bank_short_name(self) -> str | None:
        """str or None: The short name of the bank associated with the BIC.

        .. deprecated:: 2020.01.0
           Use :meth:`bank_short_names` instead.
        """
        warnings.warn("Use `BIC.bank_short_names` instead", DeprecationWarning, stacklevel=2)
        names = self.bank_short_names
        return names[0] if names else None

    @property
    def exists(self) -> bool:
        """bool: Indicates if the BIC is available in Schwifty's registry."""
        spec = registry.get("bic")
        assert isinstance(spec, dict)
        return bool(spec.get(str(self)))

    @property
    def type(self) -> str:
        """Indicates the type of BIC.

        This can be one of 'testing', 'passive', 'reverse billing' or 'default'

        Examples:
            >>> BIC('MARKDEF1100').type
            'passive'

        Returns:
            str: The BIC type.
        """
        if self.location_code[1] == "0":
            return "testing"
        elif self.location_code[1] == "1":
            return "passive"
        elif self.location_code[1] == "2":
            return "reverse billing"
        else:
            return "default"

    @property
    def country(self) -> Data | None:
        """Country: The country this BIC is registered in."""
        return countries.get(alpha_2=self.country_code)

    @property
    def bank_code(self) -> str:
        """str: The bank-code part of the BIC."""
        return self._get_component(start=0, end=4)

    @property
    def country_code(self) -> str:
        """str: The ISO 3166 alpha2 country-code."""
        return self._get_component(start=4, end=6)

    @property
    def location_code(self) -> str:
        """str: The location code of the BIC."""
        return self._get_component(start=6, end=8)

    @property
    def branch_code(self) -> str:
        """str: The branch-code part of the BIC (if available)"""
        return self._get_component(start=8, end=11)

    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        from pydantic_core import core_schema

        return core_schema.union_schema(
            [
                core_schema.is_instance_schema(BIC),
                core_schema.no_info_plain_validator_function(BIC),
            ]
        )


registry.build_index("bank", "bic", key="bic", accumulate=True)
registry.build_index(
    "bank",
    "bank_code",
    key=("country_code", "bank_code"),
    primary=True,
    accumulate=True,
)
