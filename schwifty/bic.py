from __future__ import annotations

import re
import warnings
from typing import Any
from typing import TYPE_CHECKING

from pycountry import countries  # type: ignore
from pycountry.db import Data  # type: ignore

from schwifty import common
from schwifty import exceptions
from schwifty import registry
from schwifty.domain import Bank
from schwifty.domain import canonical_bic
from schwifty.domain import lookup_rank


if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler
    from pydantic import GetJsonSchemaHandler
    from pydantic import ValidatorFunctionWrapHandler
    from pydantic.json_schema import JsonSchemaValue
    from pydantic_core import CoreSchema

_bic_iso9362_re = re.compile(r"[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?")
_bic_swift_re = re.compile(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?")

# Country codes SWIFT uses in BICs that are not (yet) part of ISO 3166-1. Kosovo's banks are
# assigned the user-assigned code XK, which the IBAN registry uses as well.
_non_iso_country_codes = frozenset({"XK"})


class BIC(common.Base):
    """The BIC object.

    When creating an instance of a BIC the provided value is checked for correctnes, unless the
    ``allow_invalid`` parameter is set to ``True``.

    The validation is done in the context of ISO 9362:2022, which allows numbers in the business
    party prefix (the first 4 chracters). If strict SWIFT compliance is required the
    ``enforce_swift_compliance`` parameter can be set to ``True``, in which case numbers are
    disallowed as described in `revision 2023`_ of the SWIFT BIC policy.

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
        bic (str): The BIC value.
        allow_invalid (bool): If set to ``True`` validation is skipped on instantiation.
        enforce_swift_commpliance (bool): If set to ``True`` the stricter SWIFT BIC policy is
                                          applied.

    Raises:
        InvalidLength: If the BIC's length is not 8 or 11 characters long.
        InvalidStructure: If the BIC contains unexpected characters.
        InvalidCountryCode: If the BIC's country code is unknown.

    .. versionchanged:: 2023.10.0
        The :class:`.BIC` is now a subclass of :class:`str` and supports all its methods.

    .. versionchanged:: 2023.11.0
        The validation of the :class:`.BIC` structure is now allowing numbers in the business party
        prefix, conforming to ISO 9362:2022. If strict SWIFT compliance should be ensured, the
        ``enforce_swift_compliance`` parameter can be set to ``True``, which will then fall back to
        the previous validation method.

    .. _revision 2023: https://www2.swift.com/knowledgecentre/rest/v1/publications/bic_policy/3.0/bic_policy.pdf
    """

    def __init__(
        self,
        bic: str,
        allow_invalid: bool = False,
        enforce_swift_compliance: bool = False,
    ) -> None:
        super().__init__()
        if not allow_invalid:
            self.validate(enforce_swift_compliance)

    @classmethod
    def candidates_from_bank_code(cls, country_code: str, bank_code: str) -> list[BIC]:
        """Create a list of potential BIC objects from country-code and domestic bank-code.

        Examples:
            >>> bic_codes = BIC.candidates_from_bank_code("FR", "30004")
            >>> bic_codes  # doctest: +ELLIPSIS
            [<BIC=BNPAFRPP>, <BIC=BNPAFRPPPXV>, <BIC=BNPAFRPPPVD>, ...]

            >>> BIC.candidates_from_bank_code("DE", "20070024")  # doctest: +ELLIPSIS
            [<BIC=DEUTDEDBHAM>, <BIC=DEUTDEDB241>, ...]

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

            * Andorra
            * Austria
            * Belgium
            * Bosnia and Herzegovina
            * Bulgaria
            * Costa Rica
            * Croatia
            * Czech Republic
            * Cyprus
            * Denmark
            * Estonia
            * Finland
            * France
            * Georgia
            * Germany
            * Greece
            * Hungary
            * Ireland
            * Iceland
            * Italy
            * Israel
            * Kazakhstan
            * Latvia
            * Liechtenstein
            * Lithuania
            * Luxembourg
            * Malta
            * Moldova
            * Monaco
            * Montenegro
            * Netherlands
            * Norway
            * Pakistan
            * Poland
            * Portugal
            * Romania
            * Saudi Arabia
            * Serbia
            * Slovakia
            * Slovenia
            * Spain
            * Sweden
            * Switzerland
            * Turkiye
            * Ukraine
            * United Arab Emirates
            * United Kingdom
        """
        banks = registry.get_banks_by_code(country_code, bank_code)
        if not banks:
            raise exceptions.InvalidBankCode(
                f"Unknown bank code {bank_code!r} for country {country_code!r}"
            )
        sorted_banks = sorted(banks, key=lookup_rank, reverse=True)
        # Bank records carry the canonical form of their BIC, so equivalent forms of the same BIC,
        # such as BNPAFRPP and BNPAFRPPXXX, are listed once.
        return [cls(bic) for bic in dict.fromkeys(entry.bic for entry in sorted_banks if entry.bic)]

    @classmethod
    def from_bank_code(cls, country_code: str, bank_code: str) -> BIC:
        """Create a new BIC object from country-code and domestic bank-code.

        Examples:
            >>> bic = BIC.from_bank_code("DE", "20070000")
            >>> bic.country_code
            'DE'
            >>> bic.bank_code
            'DEUT'
            >>> bic.location_code
            'HH'

            >>> BIC.from_bank_code("DE", "01010101")
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
            * Georgia
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
            # The candidates are ordered by rank, the same way ``IBAN.bank`` picks its record,
            # so that the BIC and the bank describe the same institution.
            return cls.candidates_from_bank_code(country_code, bank_code)[0]
        except (KeyError, IndexError) as e:
            raise exceptions.InvalidBankCode(
                f"Unknown bank code {bank_code!r} for country {country_code!r}"
            ) from e

    def validate(self, enforce_swift_compliance: bool = False) -> bool:
        """Validate the structural integrity of this BIC.

        This function will verify the correct length, structure and the existence of the country
        code.

        Args:
            enforce_swift_commpliance (bool): If set to ``True`` the stricter SWIFT BIC policy is
                                              applied, which disallows numbers in the business
                                              prefix.

        Note:
            You have to use the `allow_invalid` paramter when constructing the :class:`BIC`-object
            to circumvent the implicit validation.

        Raises:
            InvalidLength: If the BIC's length is not 8 or 11 characters long.
            InvalidStructure: If the BIC contains unexpected characters.
            InvalidCountryCode: If the BIC's country code is unknown.
        """
        self._validate_length()
        self._validate_structure(enforce_swift_compliance)
        self._validate_country_code()
        return True

    def _validate_length(self) -> None:
        if len(self) not in (8, 11):
            raise exceptions.InvalidLength(f"Invalid length '{len(self)}'")

    def _validate_structure(self, enforce_swift_compliance: bool = False) -> None:
        regex = _bic_swift_re if enforce_swift_compliance else _bic_iso9362_re
        if not regex.fullmatch(str(self)):
            raise exceptions.InvalidStructure(f"Invalid structure '{self!s}'")

    def _validate_country_code(self) -> None:
        if self.country is None and self.country_code not in _non_iso_country_codes:
            raise exceptions.InvalidCountryCode(f"Invalid country code '{self.country_code}'")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        from pydantic_core import core_schema

        return core_schema.no_info_wrap_validator_function(
            cls._pydantic_validate,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(BIC),
                    core_schema.no_info_plain_validator_function(BIC),
                    core_schema.str_schema(
                        pattern=r"[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?",
                        min_length=8,
                        max_length=11,
                    ),
                ]
            ),
            serialization=core_schema.to_string_ser_schema(
                when_used="json-unless-none",
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema["title"] = "BIC"
        return json_schema

    @classmethod
    def _pydantic_validate(cls, value: Any, handler: ValidatorFunctionWrapHandler) -> Any:
        from pydantic_core import PydanticCustomError

        try:
            bic = cls(value)
        except (exceptions.SchwiftyException, TypeError) as err:
            raise PydanticCustomError("bic_format", "{err}", {"err": str(err)}) from err
        return handler(bic)

    @property
    def is_valid(self) -> bool:
        """bool: Indicate if this is a valid BIC.

        Note:
            You have to use the `allow_invalid` paramter when constructing the :class:`BIC`-object
            to circumvent the implicit validation.

        Examples:
            >>> BIC("FOOBARBAZ", allow_invalid=True).is_valid
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
            >>> BIC("MARKDEF1100").formatted
            'MARK DE F1 100'
        """
        formatted = " ".join([self.bank_code, self.country_code, self.location_code])
        if self.branch_code:
            formatted += " " + self.branch_code
        return formatted

    @property
    def banks(self) -> list[Bank]:
        """list[Bank]: The bank records of this BIC in Schwifty's registry, the best ranked first.

        A BIC without branch code and the same BIC with the branch code ``XXX`` are treated as
        identical (see :attr:`canonical`). A branch BIC only has records if the registry lists the
        branch itself.

        The records are ranked like the lookups by bank code: active ones first, then merged ones,
        whose codes lead to a successor, then closed and delisted ones, and the primary records
        among each of them. Records of the same rank are ordered by name and bank code.

        Examples:
            >>> [bank.bank_code for bank in BIC("MARKDEF1100").banks]
            ['10000000']
            >>> BIC("REVOGB21XXX").banks == BIC("REVOGB21").banks
            True
        """
        banks = sorted(registry.get_banks_by_bic(str(self)), key=lambda b: (b.name, b.bank_code))
        # The sort is stable, so records of the same rank keep their order by name.
        return sorted(banks, key=lookup_rank, reverse=True)

    def _ranked_banks(self) -> list[Bank]:
        banks = self.banks
        if not banks and self.branch_code:
            # An 11-character BIC denotes a branch of the institution that the
            # first 8 characters identify. Not every national registry lists
            # entries per branch, so fall back to the institution's BIC when
            # the branch-specific lookup comes up empty.
            banks = BIC(str(self)[:8], allow_invalid=True).banks
        return banks

    def _lookup_values(self, key: str) -> list[str]:
        return list(
            dict.fromkeys(val for bank in self._ranked_banks() if (val := getattr(bank, key)))
        )

    @property
    def bank(self) -> Bank | None:
        """Bank | None: The best ranked bank record of this BIC, see :attr:`banks`.

        A BIC can belong to several bank codes, e.g. the ones of banks that merged into the
        institution. This is the record of the institution that services the BIC today, as far
        as the registry knows. For a branch BIC that the registry doesn't list, it is the record
        of the institution that the first 8 characters identify.

        Examples:
            >>> BIC("BSABESBB").bank.name
            'BANCO DE SABADELL, S.A.'

        .. versionadded:: 2026.11.1
        """
        banks = self._ranked_banks()
        return banks[0] if banks else None

    @property
    def domestic_bank_codes(self) -> list[str]:
        """List[str]: The country specific bank-codes associated with the BIC.

        Examples:
            >>> BIC("MARKDEF1100").domestic_bank_codes
            ['10000000']

        .. versionadded:: 2020.01.0
        """
        return self._lookup_values("bank_code")

    @property
    def bank_names(self) -> list[str]:
        """List[str]: The name of the banks associated with the BIC.

        Examples:
            >>> BIC("MARKDEF1100").bank_names
            ['Bundesbank']

        .. versionadded:: 2020.01.0
        """
        return self._lookup_values("name")

    @property
    def bank_short_names(self) -> list[str]:
        """List[str]: The short name of the banks associated with the BIC.

        Examples:
            >>> BIC("MARKDEF1100").bank_short_names
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
        """bool: Indicates if the BIC is available in Schwifty's registry.

        A BIC without branch code and the same BIC with the branch code ``XXX`` are treated as
        identical (see :attr:`canonical`). The former BIC of a merged bank exists as well, see
        :attr:`.Bank.legacy_bic`.

        Examples:
            >>> BIC("REVOGB21").exists
            True
            >>> BIC("REVOGB21XXX").exists
            True
        """
        return bool(self.banks)

    @property
    def type(self) -> str:
        """Indicates the type of BIC.

        This can be one of 'testing', 'passive', 'reverse billing' or 'default'

        Examples:
            >>> BIC("MARKDEF1100").type
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
        return self._get_slice(start=0, end=4)

    @property
    def country_code(self) -> str:
        """str: The ISO 3166 alpha2 country-code."""
        return self._get_slice(start=4, end=6)

    @property
    def location_code(self) -> str:
        """str: The location code of the BIC."""
        return self._get_slice(start=6, end=8)

    @property
    def branch_code(self) -> str:
        """str: The branch-code part of the BIC (if available)"""
        return self._get_slice(start=8, end=11)

    @property
    def canonical(self) -> BIC:
        """BIC: The BIC in the canonical form of its primary office.

        ISO 9362 treats a BIC without branch code and the same BIC with the branch code ``XXX``
        as identical. Both are returned in their 8-character form, other branch codes are kept,
        so that two BICs denote the same office if their canonical forms are equal.

        Examples:
            >>> BIC("REVOGB21XXX").canonical
            <BIC=REVOGB21>
            >>> BIC("REVOGB21").canonical
            <BIC=REVOGB21>
            >>> BIC("DEUTDEDBHAM").canonical
            <BIC=DEUTDEDBHAM>
        """
        canonical = canonical_bic(str(self))
        return self if canonical == str(self) else BIC(canonical, allow_invalid=True)
