.. _api:

Developer Interface
===================

.. module:: schwifty

IBAN
----

.. autoclass:: IBAN
   :members:

   .. attribute:: bban
      :type: BBAN

      The Basic Bank Account Number (BBAN) holds all information about national bank and account
      identifiers in a format that is decided by the national central bank or a designated payment
      authority of each country. For ease of use most of the properties of the :attr:`.bban` are
      proxied by the :class:`.IBAN`-class (e.g. :attr:`.account_code`, :attr:`.bank_code`).


BBAN
----

.. autoclass:: BBAN
   :members:


BIC
---

.. autoclass:: BIC
   :members:


Bank
----

.. autoclass:: schwifty.domain.Bank
   :members:
   :undoc-members:

.. autoclass:: schwifty.domain.BankStatus
   :members:
   :undoc-members:

.. autoclass:: schwifty.domain.SEPAScheme
   :members:
   :undoc-members:


Registry
--------

.. module:: schwifty.registry

The registries that ship with ``schwifty``, see :doc:`registries`.

.. autofunction:: get_banks_by_country
.. autofunction:: get_banks_by_code
.. autofunction:: get_banks_by_bic
.. autofunction:: get_all_banks
.. autofunction:: get_countries
.. autofunction:: get_sepa_schemes
.. autofunction:: get_iban_spec

.. autoclass:: schwifty.domain.IBANSpec
   :members:


Exceptions
----------

.. automodule:: schwifty.exceptions
   :members:
