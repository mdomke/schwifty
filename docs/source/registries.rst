Registries
==========

``schwifty`` ships with three registries, which it uses to look up banks and validate account
numbers. You can also query them directly, e.g. to list the banks of a country or to find out
whether a bank can be reached for SEPA direct debits.

* The **bank registry** maps the bank codes of 47 countries to their banks and BICs.
* The **SCL directory** lists the SEPA schemes that payment service providers take part in.
* The **IBAN registry** describes the format of the IBANs and national account numbers of 127
  countries.

The registries are updated with each release. That's why ``schwifty`` uses calendar versioning:
a newer version comes with more recent data.


Bank registry
-------------

The bank registry records for each bank code the bank's name and BIC, whether the bank is still
active, and for German banks the check digit method of their account numbers (see
:doc:`national-accounts`). The :class:`.IBAN`, :class:`.BBAN` and :class:`.BIC` classes use it to
look up banks, but you can query it directly with the functions of :mod:`schwifty.registry`:

.. code-block:: pycon

  >>> from schwifty import registry
  >>> registry.get_banks_by_code("DE", "37040044")
  [Bank(country_code='DE', bic='COBADEFF', bank_code='37040044', name='Commerzbank', ...)]
  >>> len(registry.get_banks_by_bic("COBADEFF"))
  285
  >>> len(registry.get_banks_by_country("IE"))
  273

Where they are available, the registries are generated from the official sources of central banks
and banking associations. Bank codes that drop out of these sources are kept, because IBANs that
carry them stay in circulation, and their status tells what became of them (see
:ref:`retired bank codes <retired-bank-codes>`).

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Country
     - Source
   * - Austria
     - Oesterreichische Nationalbank
   * - Belgium
     - National Bank of Belgium
   * - Croatia
     - Croatian National Bank
   * - Czech Republic
     - Czech National Bank
   * - Estonia
     - Estonian Banking Association
   * - Finland
     - Finance Finland
   * - France, Monaco
     - REGAFI, the register of the Autorité de contrôle prudentiel et de résolution, with BICs from
       GLEIF
   * - Georgia
     - National Bank of Georgia
   * - Germany
     - Deutsche Bundesbank
   * - Hungary
     - Magyar Nemzeti Bank
   * - Ireland, Malta
     - SCL directory of the Deutsche Bundesbank
   * - Italy
     - Banca d'Italia, with BICs from GLEIF
   * - Latvia
     - Latvijas Banka
   * - Liechtenstein, Switzerland
     - SIX Interbank Clearing
   * - Lithuania
     - Lietuvos bankas
   * - Netherlands
     - Betaalvereniging Nederland
   * - Norway
     - Bits AS
   * - Poland
     - Narodowy Bank Polski
   * - Romania, United Kingdom
     - GLEIF's BIC-to-LEI mapping
   * - Slovakia
     - Národná banka Slovenska
   * - Slovenia
     - Banka Slovenije
   * - Spain
     - iban.es
   * - Sweden
     - Bankinfrastruktur i Sverige
   * - Ukraine
     - National Bank of Ukraine

The registries of Andorra, Bosnia and Herzegovina, Bulgaria, Costa Rica, Cyprus, Denmark, Greece,
Iceland, Israel, Kazakhstan, Luxembourg, Moldova, Montenegro, Pakistan, Portugal, Saudi Arabia,
Serbia, Turkiye and the United Arab Emirates are maintained by hand.


SCL directory
-------------

The SCL directory of the Deutsche Bundesbank lists the BICs of about 4,700 payment service
providers that can be reached through its SEPA clearer, together with the SEPA schemes they take
part in: credit transfers, core and business-to-business direct debits, and card clearing. Since it
covers most banks of the SEPA area, it tells for example whether you can collect a direct debit from
an account:

.. code-block:: pycon

  >>> from schwifty import IBAN
  >>> from schwifty.domain import SEPAScheme
  >>> SEPAScheme.CORE_DIRECT_DEBIT in IBAN("DE89 3704 0044 0532 0130 00").sepa_schemes
  True
  >>> registry.get_sepa_schemes("DEUTDEDBPAL")
  frozenset({<SEPAScheme.CREDIT_TRANSFER: 'SCT'>})

See :ref:`SEPA schemes <sepa-schemes>` for details. :func:`.registry.get_sepa_schemes`
returns ``None`` for a BIC that the directory doesn't list, while :attr:`.BIC.sepa_schemes` falls
back to the schemes of the institution for a branch BIC. The directory doesn't cover SEPA Instant
Credit Transfers.


IBAN registry
-------------

The IBAN registry is generated from the IBAN registry of SWIFT, which covers 105 countries, and
amended with 22 countries that use IBANs without being part of it, such as Morocco or Senegal. For
each country it describes the format of the IBAN and of the national account number, the position
of their components, and whether the country is part of the SEPA area:

.. code-block:: pycon

  >>> spec = registry.get_iban_spec("DE")
  >>> spec.iban_spec, spec.iban_length, spec.in_sepa_zone
  ('DE2!n8!n10!n', 22, True)
  >>> registry.get_iban_spec("MA").aspirational
  True

The formats use the notation of the SWIFT IBAN registry, e.g. ``8!n`` for exactly eight digits.
IBANs of the countries that are not part of the SWIFT registry are marked as *aspirational*, see
:attr:`.IBAN.is_aspirational`.
