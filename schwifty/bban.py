from __future__ import annotations

from typing import Any

from schwifty import common
from schwifty import exceptions
from schwifty import registry
from schwifty.bic import BIC
from schwifty.checksum import algorithms
from schwifty.domain import Component


try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

EMPTY_RANGE = (0, 0)


def _get_bban_spec(country_code: str) -> dict[str, Any]:
    try:
        spec = registry.get("iban")
        assert isinstance(spec, dict)
        return spec[country_code]
    except KeyError as e:
        raise exceptions.InvalidCountryCode(f"Unknown country-code '{country_code}'") from e


def _get_position_range(spec: dict[str, Any], component_type: Component) -> tuple[int, int]:
    return spec.get("positions", {}).get(component_type, EMPTY_RANGE)


def calc_value_length(spec: dict[str, Any], component_type: Component) -> int:
    start, end = _get_position_range(spec, component_type)
    return end - start


def compute_national_checksum(country_code: str, components: dict[Component, str]) -> str:
    algo = algorithms.get(f"{country_code}:default")
    if algo is None:
        return ""

    return algo.compute([components[key] for key in algo.accepts])


class BBAN(common.Base):
    """The Basic Bank Account Number (BBAN).

    The format is decided by the national central bank or designated payment authority of each
    country.

    Examples:

        Most commonly :class:`.BBAN`-objects are created implicitly by the :class:`.IBAN`-class, but
        they can also be instantiated like so::

            >>> BBAN.from_components("DE", account_code="0532013000", bank_code="37040044")
            <BBAN=370400440532013000>

    Args:
        country_code (str): A two-letter ISO 3166-1 compliant country code
        value (str): The country specific BBAN value.

    .. versionadded:: 2024.01.1
    """

    def __new__(cls: type[Self], country_code: str, value: str, **kwargs: Any) -> Self:
        return super().__new__(cls, value, **kwargs)

    def __init__(self, country_code: str, value: str) -> None:
        self.country_code = country_code

    @classmethod
    def from_components(cls, country_code: str, **values: str) -> BBAN:
        """Generate a BBAN from its national components.

        The currently supported ``values`` are ``bank_code``, ``branch_code`` and ``account_code``.

        Args:
            country_code (str): The ISO 3166 alpha-2 country code.
            values: The country specific BBAN components.

        Raises:
            InvalidAccountCode: If the account code does not meet the national requirements.
        """
        spec: dict[str, Any] = _get_bban_spec(country_code)
        if "positions" not in spec:
            raise exceptions.SchwiftyException(f"BBAN generation for {country_code} not supported")

        bank_code_length: int = calc_value_length(spec, Component.BANK_CODE)
        branch_code_length: int = calc_value_length(spec, Component.BRANCH_CODE)
        account_code_length: int = calc_value_length(spec, Component.ACCOUNT_CODE)

        country_code = common.clean(country_code)
        bank_code = common.clean(values.get("bank_code", ""))
        account_code = common.clean(values.get("account_code", ""))
        branch_code = common.clean(values.get("branch_code", ""))

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

        components = {
            Component.BANK_CODE: bank_code.zfill(bank_code_length),
            Component.BRANCH_CODE: branch_code.zfill(branch_code_length),
            Component.ACCOUNT_CODE: account_code.zfill(account_code_length),
        }
        components[Component.NATIONAL_CHECKSUM_DIGITS] = compute_national_checksum(
            country_code, components
        )

        bban = "0" * spec["bban_length"]
        for key, value in components.items():
            position_range = _get_position_range(spec, key)
            if position_range == EMPTY_RANGE:
                continue
            end = position_range[1]
            start = end - len(value)
            bban = bban[:start] + value + bban[end:]

        return cls(country_code, bban)

    def validate_national_checksum(self) -> bool:
        """bool: Validate the national checksum digits.

        Raises:
            InvalidBBANChecksum: If the country specific BBAN checksum is invalid.
        """
        bank = self.bank or {}
        algo_name = bank.get("checksum_algo", "default")
        algo = algorithms.get(f"{self.country_code}:{algo_name}")
        if algo is None:
            return True
        components = [self._get_component(component) for component in algo.accepts]
        if not algo.validate(components, self.national_checksum_digits):
            raise exceptions.InvalidBBANChecksum("Invalid national checksum")
        return False

    def _get_component(self, component_type: Component) -> str:
        start, end = _get_position_range(self.spec, component_type)
        return self._get_slice(start, end)

    @property
    def spec(self) -> dict[str, Any]:
        """dict: The country specific BBAN specification."""
        return _get_bban_spec(self.country_code)

    @property
    def bic(self) -> BIC | None:
        """BIC or None: The BIC associated to the BBAN's bank-code.

        If the bank code is not available in schwifty's registry ``None`` is returned.
        """
        lookup_by = self.spec.get("bic_lookup_components", [Component.BANK_CODE])
        key = "".join(self._get_component(component) for component in lookup_by)
        try:
            return BIC.from_bank_code(self.country_code, key)
        except exceptions.SchwiftyException:
            return None

    @property
    def national_checksum_digits(self) -> str:
        """str: National checksum digits if available."""
        return self._get_component(Component.NATIONAL_CHECKSUM_DIGITS)

    @property
    def bank_code(self) -> str:
        """str: The country specific bank-code."""
        return self._get_component(Component.BANK_CODE)

    @property
    def branch_code(self) -> str:
        """str: The branch-code of the bank if available."""
        return self._get_component(Component.BRANCH_CODE)

    @property
    def account_code(self) -> str:
        """str: The domestic account-code"""
        return self._get_component(Component.ACCOUNT_CODE)

    @property
    def account_id(self) -> str:
        """str: Holder specific account identification.

        This is currently only available for Brazil.
        """
        return self._get_component(Component.ACCOUNT_ID)

    @property
    def account_type(self) -> str:
        """str: Account type specifier.

        This value is only available for Seychelles, Brazil and Bulgaria.
        """
        return self._get_component(Component.ACCOUNT_TYPE)

    @property
    def account_holder_id(self) -> str:
        """str: Account holder's national identification.

        This value is only available for Iceland.
        """
        return self._get_component(Component.ACCOUNT_HOLDER_ID)

    @property
    def bank(self) -> dict | None:
        """dict | None: The information of bank related to this BBANs bank code."""
        bank_registry = registry.get("bank_code")
        assert isinstance(bank_registry, dict)
        bank_entry = bank_registry.get((self.country_code, self.bank_code or self.branch_code))
        if not bank_entry:
            return None
        return bank_entry and bank_entry[0]

    @property
    def bank_name(self) -> str | None:
        """str or None: The name of the bank associated with the IBAN bank code.

        Examples:
            >>> IBAN('DE89370400440532013000').bank_name
            'Commerzbank'
        """
        return None if self.bank is None else self.bank["name"]

    @property
    def bank_short_name(self) -> str | None:
        """str or None: The name of the bank associated with the IBAN bank code.

        Examples:
            >>> IBAN('DE89370400440532013000').bank_short_name
            'Commerzbank Köln'
        """
        return None if self.bank is None else self.bank["short_name"]


registry.build_index("bank", "country", key="country_code", accumulate=True)
