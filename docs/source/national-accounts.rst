National account numbers
========================

Every IBAN is built around a national account number, the BBAN (Basic Bank Account Number), whose
format is decided by the central bank or payment authority of each country. Many countries protect
it with their own check digits, e.g. the RIB key in France, the *dígitos de control* in Spain or the
check digit methods of German banks. ``schwifty`` implements these algorithms, so you can validate
and complete domestic account numbers, also where no IBAN is involved.


Working with a BBAN
-------------------

A :class:`.BBAN` is created from a country code and the national account number. It splits the
number into its components and knows the bank behind it, just like an :class:`.IBAN`:

.. code-block:: pycon

  >>> from schwifty import BBAN
  >>> bban = BBAN("DE", "370400440532013000")
  >>> bban.bank_code, bban.account_code
  ('37040044', '0532013000')
  >>> bban.bank_name, bban.bic
  ('Commerzbank', <BIC=COBADEFF>)

:meth:`.BBAN.validate_national_checksum` verifies the national check digits and raises
:exc:`.InvalidBBANChecksum` if they don't match:

.. code-block:: pycon

  >>> bban.validate_national_checksum()
  True
  >>> BBAN("DE", "370400440532014000").validate_national_checksum()
  ...
  InvalidBBANChecksum: Invalid national checksum

The components of a BBAN differ from country to country. A French BBAN, for example, consists of a
bank code, a branch code (*code guichet*), an account code and the RIB key as national check
digits:

.. code-block:: pycon

  >>> bban = BBAN("FR", "20041010050500013M02606")
  >>> bban.bank_code, bban.branch_code, bban.account_code, bban.national_checksum_digits
  ('20041', '01005', '0500013M026', '06')


Computing check digits
----------------------

:meth:`.BBAN.from_components` assembles a BBAN from its components and computes the national check
digits for you. Missing leading zeros are added as well:

.. code-block:: pycon

  >>> BBAN.from_components("ES", bank_code="2100", branch_code="0418", account_code="0200051332")
  <BBAN=21000418450200051332>
  >>> BBAN.from_components("FR", bank_code="20041", branch_code="01005", account_code="0500013M026")
  <BBAN=20041010050500013M02606>
  >>> BBAN.from_components("DE", bank_code="37040044", account_code="532013000")
  <BBAN=370400440532013000>

:meth:`.IBAN.generate` does the same when it creates an IBAN, and :meth:`.BBAN.random` generates
random account numbers whose national check digits are valid, which is useful for test data.


Supported countries
-------------------

The national check digits of the following countries are validated:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Country
     - Algorithm
   * - Belgium
     - MOD 97 over the bank and account code
   * - Bosnia and Herzegovina, Kosovo, Montenegro, North Macedonia, Portugal, Serbia, Slovenia,
       Timor-Leste
     - ISO 7064 MOD 97-10 over the BBAN
   * - Czech Republic, Slovakia
     - Weighted MOD 11 over the account number prefix and the account number
   * - Estonia
     - Weights 7-3-1 over the branch and account code
   * - Finland
     - Luhn algorithm over the bank and account code
   * - France, Monaco
     - RIB key (*clé RIB*)
   * - Germany
     - The check digit method of each bank, as published by the Deutsche Bundesbank
   * - Iceland
     - Check digit of the account holder's national identification number (*kennitala*)
   * - Italy, San Marino
     - CIN (*Control Internal Number*)
   * - Mauritania, Tunisia
     - ISO 7064 MOD 97-10 with the complement to 97
   * - Norway
     - Weighted MOD 11 over bank and account number
   * - Poland
     - Weighted MOD 10 over the bank sort code
   * - Spain
     - Two *dígitos de control*, weighted MOD 11 over bank and branch code and over the account
       code

German banks choose one of the check digit methods defined by the Deutsche Bundesbank, which the
bank registry records as :attr:`.Bank.checksum_algo`. Of the 91 methods in use, ``schwifty``
implements the 50 that cover about 98% of all active German bank codes. The check digits of bank
codes whose method isn't implemented are accepted as they are.

Where a country's BBAN format declares national check digits, but ``schwifty`` has no algorithm for
them, e.g. in Hungary, the digits are accepted as they are. The check that didn't happen is
reported with the :class:`.NationalChecksumNotVerified` warning, which you can turn into an error
if the check is mandatory for your use case:

.. code-block:: pycon

  >>> import warnings
  >>> from schwifty.exceptions import NationalChecksumNotVerified
  >>> warnings.simplefilter("error", NationalChecksumNotVerified)
  >>> BBAN("HU", "117730161111101800000000").validate_national_checksum()
  ...
  NationalChecksumNotVerified: No national checksum algorithm is registered for HU: the national
  check digits were not verified
