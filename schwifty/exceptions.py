class SchwiftyException(ValueError):  # noqa: N818
    """Base exception of all schwifty related errors."""


class InvalidLength(SchwiftyException):
    """Indicates that the length of the input does not match the specification."""


class InvalidStructure(SchwiftyException):
    """Indicates a structural error of the input (e.g. invalid characters)."""


class InvalidCountryCode(SchwiftyException):
    """Unknown country code in the input."""


class InvalidBankCode(SchwiftyException):
    """Indicates that the bank code has an invalid structure."""


class InvalidBranchCode(SchwiftyException):
    """Indicates that the branch code has an invalid structure."""


class InvalidAccountCode(SchwiftyException):
    """Indicates that the account code has an invalid structure."""


class InvalidChecksumDigits(SchwiftyException):
    """Indicates that the IBAN's checksum is invalid."""


class InvalidBBANChecksum(SchwiftyException):
    """Indicates that the BBAN's checksum is invalid."""


class NationalChecksumNotVerified(UserWarning):
    """Indicates that national check digits were accepted without being verified.

    The country's BBAN specification declares a national check-digit field, but no algorithm is
    registered to verify it. A missing algorithm must not reject an otherwise valid BBAN, so the
    digits are taken as they are. Callers that require the check to fail instead can turn the
    warning into an error with ``warnings.simplefilter("error", NationalChecksumNotVerified)``.
    """


class GenerateRandomOverflowError(SchwiftyException):
    """Indicates that during random entity generation no valid value could be found.

    This could for example be the case if the national checksum digit does not compute for
    a randomly chosen account code.
    """
