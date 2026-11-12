IBANs and BICs by example
=========================

Basics
------

:class:`.IBAN`-objects are usually created from their string representation

.. code-block:: pycon

  >>> from schwifty import IBAN
  >>> iban = IBAN('DE89 3704 0044 0532 0130 00')
  <IBAN=DE89370400440532013000>


Afterwards, you can access all relevant components and meta-information of the IBAN as attributes.

.. code-block:: pycon

  >>> str(iban)
  'DE89370400440532013000'
  >>> iban.formatted
  'DE89 3704 0044 0532 0130 00'
  >>> iban.country_code
  'DE'
  >>> iban.bank_code
  '37040044'
  >>> iban.account_code
  '0532013000'
  >>> len(iban)
  22
  >>> iban.bban
  <BBAN=370400440532013000>

For many countries it is also possible to get the :class:`.BIC` and the bank associated to the
bank-code of the IBAN.

.. code-block:: pycon

  >>> iban.bic
  <BIC=COBADEFF>

A BIC is a unique identification code for both financial and non-financial institutes. ``schwifty``
provides a :class:`.BIC`-object, that has a similar interface to the :class:`.IBAN`.

.. code-block:: pycon

  >>> from schwifty import BIC
  >>> bic = BIC('PBNKDEFFXXX')
  >>> bic.bank_code
  'PBNK'
  >>> bic.branch_code
  'XXX'
  >>> bic.country_code
  'DE'
  >>> bic.location_code
  'FF'
  >>> bic.domestic_bank_codes
  ['10010010',
   '20010020',
   ...
   '86010090']

The :attr:`.BIC.domestic_bank_codes` lists the country specific bank codes as you can find them as
part of the IBAN. A BIC can belong to several bank codes, e.g. the ones of banks that merged into
the institution. The lists of a BIC are therefore ordered like the lookups by bank code: active
banks before merged, closed and delisted ones. :attr:`.BIC.bank` is the best ranked bank record,
the institution that services the BIC today:

.. code-block:: pycon

  >>> BIC('BSABESBB').bank.name
  'BANCO DE SABADELL, S.A.'

The mapping is included in the bank registry that ships with ``schwifty``, which covers 47
countries. See :doc:`registries` for the list of countries and their sources.

.. note::

  The :class:`.IBAN` and :class:`.BIC` classes are subclasses of :class:`str` so that all methods
  and functionalities (e.g. slicing) can be directly used. E.g.

  .. code-block:: pycon

    >>> iban = IBAN('DE89 3704 0044 0532 0130 00')
    >>> iban[2:4]
    "89"
    >>> iban.count("0")
    8
    >>> iban.startswith("DE")
    True

.. _retired-bank-codes:

Retired bank codes
~~~~~~~~~~~~~~~~~~

Banks merge or close, but IBANs with their bank codes stay in circulation. ``schwifty`` keeps such
retired bank codes in its registry. :attr:`.Bank.status` tells what became of them: ``merged``,
``closed``, or ``delisted`` if the source doesn't say why it no longer lists the code. The code of
a merged bank resolves to the bank that services it today:

.. code-block:: pycon

  >>> iban = IBAN.generate("DE", bank_code="13061088", account_code="1234567")
  >>> iban.bank.name, iban.bank.status, iban.bank.successor_bank_code
  ('Volks- und Raiffeisenbank', <BankStatus.MERGED: 'merged'>, '13061078')

The name and BIC of the merged bank are kept, and its BIC still resolves to its retired bank code:

.. code-block:: pycon

  >>> iban.bank.legacy_name, iban.bank.legacy_bic, iban.bic
  ('Raiffeisenbank Wismar', 'GENODEF1HWR', <BIC=GENODEF1HWI>)
  >>> BIC("GENODEF1HWR").domestic_bank_codes
  ['13061088']

A bank that was closed, or is no longer listed without a known successor, is still returned, so
that an IBAN can be identified. No payments can be made to it, though, so check its status before
you initiate one:

.. code-block:: pycon

  >>> iban = IBAN.generate("DE", bank_code="29020200", account_code="1234567890")
  >>> iban.bank.name, iban.bank.status
  ('Greensill Bank', <BankStatus.DELISTED: 'delisted'>)

.. _sepa-schemes:

SEPA schemes
~~~~~~~~~~~~

:attr:`.BIC.sepa_schemes` tells which SEPA schemes the institution of a BIC takes part in: credit
transfers, core and business-to-business direct debits, and card clearing. The schemes are taken
from the SCL directory of the Deutsche Bundesbank, which lists the payment service providers that
can be reached through its SEPA clearer:

.. code-block:: pycon

  >>> from schwifty.domain import SEPAScheme
  >>> SEPAScheme.CORE_DIRECT_DEBIT in BIC("AACSDE33").sepa_schemes
  True
  >>> BIC("DEUTDEDBPAL").sepa_schemes
  frozenset({<SEPAScheme.CREDIT_TRANSFER: 'SCT'>})

A branch BIC that the directory doesn't list has the schemes of its institution. The set is empty
for a BIC that the directory doesn't list at all, which means that its participation is unknown.
SEPA Instant Credit Transfers are not covered by the directory.

:attr:`.IBAN.sepa_schemes` returns the schemes of the IBAN's bank, so that you can e.g. check
whether a direct debit can be collected from an account. Its set is also empty if the registry
doesn't know a BIC for the bank code. Unlike :attr:`.IBAN.in_sepa_zone`, which tells whether the
account's country takes part in SEPA, it tells whether its bank does:

.. code-block:: pycon

  >>> iban = IBAN("DE89 3704 0044 0532 0130 00")
  >>> iban.in_sepa_zone, SEPAScheme.CORE_DIRECT_DEBIT in iban.sepa_schemes
  (True, True)


Validation
----------

When it comes to validation the :class:`.IBAN` and :class:`.BIC` constructors raise an exception
whenever the provided code is incorrect for some reason. ``schwifty`` comes with a number of
dedicated exceptions classes that help identify the concrete reason for the validation error. They
all derive from a common base exception :exc:`.SchwiftyException` which makes it easy to catch all
validation failures if the concrete cause is not important to you.

.. note::

   Prior to schwifty 2021.01.0 a ``ValueError`` was raised for all kind of validation failures. In
   order to keep backwards compatibility schwifty's base exception is a subclass of ``ValueError``.

For IBANs - with respect to ISO 13616 compliance - it is checked if the account-code, the bank-code
and possibly the branch-code have the correct country-specific format. E.g.:

.. code-block:: pycon

  >>> IBAN('DX89 3704 0044 0532 0130 00')
  ...
  InvalidCountryCode: Unknown country-code DX

  >>> IBAN('DE99 3704 0044 0532 0130 00')
  ...
  InvalidChecksumDigits: Invalid checksum digits

``schwifty`` can also validate the national check digits within the BBAN for 24 countries (see
:doc:`national-accounts`). This validation is opt-in and can be used by providing the
``validate_bban`` parameter to the :class:`.IBAN` constructor or the :meth:`.IBAN.validate`-method.

.. code-block:: pycon

   >>> iban = IBAN('DE20 2909 0900 8840 0170 00')
   >>> iban.validate(validate_bban=True)
   ...
   InvalidBBANChecksum: Invalid BBAN checksum

   >>> IBAN('DE20 2909 0900 8840 0170 00', validate_bban=True)
   ...
   InvalidBBANChecksum: Invalid BBAN checksum

Not every country's national checksum is implemented. Where a country's BBAN specification declares
check digits but ``schwifty`` has no algorithm for them, the digits are accepted as they are -- a
missing algorithm must not reject an otherwise valid IBAN -- and the check that did not happen is
reported with the :class:`.NationalChecksumNotVerified` warning. If the check is mandatory for your
use case, turn the warning into an error:

.. code-block:: pycon

   >>> import warnings
   >>> warnings.simplefilter('error', NationalChecksumNotVerified)
   >>> IBAN('HU42 1177 3016 1111 1018 0000 0000', validate_bban=True)
   ...
   NationalChecksumNotVerified: No national checksum algorithm is registered for HU ...

For BICs it is checked if the country-code and the length is valid and if the structure matches the
ISO 9362 specification.

.. code-block:: pycon

  >>> BIC('PBNKDXFFXXX')
  ...
  InvalidCountryCode: Invalid country code DX

  >>> BIC('PBNKDXFFXXXX')
  ...
  InvalidLength: Invalid length 12

  >>> BIC('PBNKD1FF')
  ...
  InvalidStructure: Invalid structure 'PBNKD1FF'

.. note::

  Starting from schwifty 2023.11.0 BIC values are being validated in the context of ISO 9362:2022
  which allows numbers to be part of the business prefix (the first 4 characters of the BIC). The
  SWIFT however still enforces alphabetic characters only. If strict SWIFT compliance is required
  you can use the ``enforce_swift_compliance``-parameter, e.g.

  .. code-block:: pycon

    >>> BIC("1234DEWWXXX", enforce_swift_compliance=True)
    ...
    InvalidStructure: Invalid structure 1234DEWWXXX

If catching an exception would complicate your code flow you can also use the :attr:`.IBAN.is_valid`
property. E.g.:

.. code-block:: python

  if IBAN(value, allow_invalid=True).is_valid:
    # do something with value


This will however not validate the national checksum digits.


Generation
----------

You can generate :class:`.IBAN`-objects from country-code, bank-code and account-number by using the
:meth:`.IBAN.generate()`-method. It will automatically calculate the correct checksum digits for
you.

.. code-block:: pycon

  >>> iban = IBAN.generate('DE', bank_code='10010010', account_code='12345')
  <IBAN=DE40100100100000012345>
  >>> iban.checksum_digits
  '40'

Notice that even that the account-code has less digits than required (in Germany accounts should be
10 digits long), zeros have been added at the correct location.

For many countries that have a national checksum as part of the BBAN, its value is automatically
calculated upon IBAN generation. E.g.

.. code-block:: pycon

  >>> iban = IBAN.generate("ES", "2100", "0200051332", "0418")
  <IBAN=ES9121000418450200051332>
  >>> iban.bban.national_checksum_digits
  '45'

For some countries you can also generate :class:`.BIC`-objects from local
bank-codes, e.g.:

.. code-block:: pycon

  >>> bic = BIC.from_bank_code('DE', '43060967')
  >>> bic.formatted
  'GENO DE M1 GLS'

In case there are multiple BICs that can be related to a domestic bank code you can also use the
:meth:`.BIC.candidates_from_bank_code`-method to get a list of all known BIC candidates.

.. code-block:: pycon

  >>> BIC.candidates_from_bank_code('FR', '30004') # doctest: +NORMALIZE_WHITESPACE
  [<BIC=BNPAFRPP>, <BIC=BNPAFRPPPXV>, <BIC=BNPAFRPPPVD>, <BIC=BNPAFRPPPTX>, <BIC=BNPAFRPPPLZ>,
   <BIC=BNPAFRPPPGN>, <BIC=BNPAFRPPPEE>, <BIC=BNPAFRPPPBQ>, <BIC=BNPAFRPPPAE>, <BIC=BNPAFRPPPAC>,
   <BIC=BNPAFRPPPAA>, <BIC=BNPAFRPPORE>, <BIC=BNPAFRPPNFE>, <BIC=BNPAFRPPNEU>, <BIC=BNPAFRPPMED>,
   <BIC=BNPAFRPPIFO>, <BIC=BNPAFRPPIFN>, <BIC=BNPAFRPPENG>, <BIC=BNPAFRPPCRN>, <BIC=BNPAFRPPCRM>,
   <BIC=BNPAFRPPBOR>, <BIC=BNPAFRPP039>]


Random IBANs
~~~~~~~~~~~~

For testing and other use cases it might be useful to generate random IBANs. Therefore you can
simply call

.. code-block:: pycon

  >>> IBAN.random()
  <IBAN=IT53D0838265738IXCFNXEVWPNL>

and you will get a random but valid IBAN. You can also predefine some parameters of the random
result to narrow down the possible values, e.g.

.. code-block:: pycon

  >>> IBAN.random(country_code="GB")
  <IBAN=GB67COBA74887171221908>

will give you a British IBAN. Similarly,

.. code-block:: pycon

  >>> IBAN.random(country_code="GB", bank_code="LOYD")
  <IBAN=GB53LOYD00952296262556>

will only give you IBANs from the Lloyds Bank.

Notice that for countries that have a bank registry, the bank code will be taken from there, so
that the IBAN corresponds to a valid bank. E.g.:

.. code-block:: pycon

  >>> IBAN.random(country_code="DE").bank
  Bank(country_code='DE', bic='BOTKDEDX', bank_code='30010700',
       name='MUFG Bank (Europe) Germany Branch', ...)

If you want to generate an IBAN with a truly random bank code use

.. code-block:: pycon

  >>> IBAN.random(country_code="DE", use_registry=False).bank
  None

Due to the nature of random numbers you might still hit a valid bank code once in a while.

Pydantic integration
--------------------

The :class:`.IBAN` and :class:`.BIC` types can be directly used for the popular data validation
library `Pydantic <https://docs.pydantic.dev/latest/>`_ like so

.. code-block:: python

  from pydantic import BaseModel
  from schwifty import IBAN


  class Model(BaseModel):
    iban: IBAN

  model = Model(iban="DE89370400440532013000")  # OK
  model = Model(iban="DX89370400440532013000")  # Raises ValidationError due to invalid country code


You can also allow invalid values (think ``IBAN(allow_invalid=True)``) with


.. code-block:: python

  from typing import Annotated

  from pydantic import BaseModel
  from pydantic import Field
  from schwifty import IBAN


  class Model(BaseModel):
    iban: Annotated[IBAN, Field(strict=False)]

  model = Model(iban="DX89370400440532013000")  # OK, even though the country code is incorrect
