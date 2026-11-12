.. image:: https://img.shields.io/pypi/v/schwifty.svg?style=flat-square
    :target: https://pypi.python.org/pypi/schwifty
.. image:: https://img.shields.io/github/actions/workflow/status/mdomke/schwifty/lint-and-test.yml?branch=main&style=flat-square
    :target: https://github.com/mdomke/schwifty/actions?query=workflow%3Alint-and-test
.. image:: https://img.shields.io/pypi/l/schwifty.svg?style=flat-square
    :target: https://pypi.python.org/pypi/schwifty
.. image:: https://readthedocs.org/projects/schwifty/badge/?version=latest&style=flat-square
    :target: https://schwifty.readthedocs.io
.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square
    :target: https://github.com/astral-sh/ruff
.. image:: https://img.shields.io/codecov/c/gh/mdomke/schwifty?token=aJj1Yg0NUq&style=flat-square
    :target: https://codecov.io/gh/mdomke/schwifty


Gotta get schwifty with your IBANs
==================================

.. teaser-begin

``schwifty`` is a Python library for working with bank account numbers and bank identifiers: IBANs
(International Bank Account Numbers, ISO 13616), BICs (Business Identifier Codes, ISO 9362) and
the national account numbers they are built from. It brings the knowledge needed to work with them
along: the format of the account numbers of 127 countries, the national check digit algorithms of
24 of them, bank registries for 47 countries generated from their official sources, and the SEPA
schemes that banks take part in.

.. code-block:: pycon

  >>> from schwifty import IBAN
  >>> iban = IBAN("DE89 3704 0044 0532 0130 00", validate_bban=True)
  >>> iban.bank_code, iban.account_code
  ('37040044', '0532013000')
  >>> iban.bank.name, iban.bic
  ('Commerzbank', <BIC=COBADEFF>)
  >>> from schwifty.domain import SEPAScheme
  >>> SEPAScheme.CORE_DIRECT_DEBIT in iban.sepa_schemes
  True

Features
--------

**IBANs**

* `validate`_ the check digits and the country specific format of IBANs, for the 105 countries of
  the SWIFT IBAN registry and 22 countries that use IBANs without being part of it
* `generate`_ IBANs from country code, bank code and account number, including the national check
  digits, or `random`_ but valid ones for testing
* access all components, e.g. bank code, branch code and account code, as attributes
* use the ``IBAN`` and ``BIC`` types directly in `Pydantic`_ models

**National account numbers**

* `validate`_ and compute the `national check digits`_ of domestic account numbers for 24 countries,
  with or without an IBAN, e.g. the check digit methods of German banks, the French RIB key or
  the Spanish *dígitos de control*

**BICs and banks**

* `validate`_ the structure and country of BICs, and convert between bank codes and BICs
* look up the bank behind a bank code or BIC in `bank registries`_ for 47 countries, generated
  from the official sources of central banks and banking associations where they are available
* identify `retired bank codes`_ that IBANs in circulation still carry, and tell whether their
  bank merged into another one or closed
* check which `SEPA schemes`_ the bank of an IBAN or BIC takes part in, from the SCL directory of
  the Deutsche Bundesbank

See the `docs <https://schwifty.readthedocs.io>`_ for more information.

.. _validate: https://schwifty.readthedocs.io/en/latest/examples.html#validation
.. _generate: https://schwifty.readthedocs.io/en/latest/examples.html#generation
.. _random: https://schwifty.readthedocs.io/en/latest/examples.html#random-ibans
.. _Pydantic: https://schwifty.readthedocs.io/en/latest/examples.html#pydantic-integration
.. _national check digits: https://schwifty.readthedocs.io/en/latest/national-accounts.html
.. _bank registries: https://schwifty.readthedocs.io/en/latest/registries.html
.. _retired bank codes: https://schwifty.readthedocs.io/en/latest/examples.html#retired-bank-codes
.. _SEPA schemes: https://schwifty.readthedocs.io/en/latest/examples.html#sepa-schemes

.. teaser-end

Versioning
----------

Since the IBAN specification and the mapping from BIC to bank_code is updated from time to time,
``schwifty`` uses `CalVer <http://www.calver.org/>`_ for versioning with the scheme ``YY.0M.Micro``.


.. installation-begin

Installation
------------

To install ``schwifty``, simply:

.. code-block:: bash

  $ pip install schwifty

.. installation-end


Development
-----------

The only prerequisite to work on ``schwifty`` is `uv`_. Running ``uv sync`` creates a virtual
environment with all development dependencies (including the tools mentioned below).

We use `ruff`_ as code formatter and linter. This avoids discussions about style preferences in the
same way as ``gofmt`` does the job for Golang. The conformance to the formatting rules is checked in
the CI pipeline, so that it is recommendable to install the configured `prek`_-hook, in order
to avoid long feedback-cycles.

.. code-block:: bash

   $ uv sync --all-groups --all-extras
   $ uv run prek install

You can also run ``uv run poe fmt`` to format the code or use one of the available `editor
integrations`_. See the `contributing guide`_ for the full list of development commands and the
contribution workflow.


Project Information
-------------------

``schwifty`` is released under `MIT`_ license and its documentation lives at `Read the Docs`_. The
code is maintained on `GitHub`_ and packages are distributed on `PyPI`_

Name
~~~~

Since ``swift`` and ``swiftly`` were already taken by the OpenStack-project, but we somehow wanted
to point out the connection to SWIFT, Rick and Morty came up with the idea to name the project
``schwifty``.

.. image:: https://i.cdn.turner.com/adultswim/big/video/get-schwifty-pt-2/rickandmorty_ep205_002_vbnuta15a755dvash8.jpg


.. _uv: https://docs.astral.sh/uv/
.. _contributing guide: https://github.com/mdomke/schwifty/blob/main/CONTRIBUTING.rst
.. _ruff: https://docs.astral.sh/ruff/
.. _prek: https://prek.j178.dev
.. _editor integrations:  https://docs.astral.sh/ruff/editors/
.. _MIT: https://choosealicense.com/licenses/mit/
.. _Read the Docs: https://schwifty.readthedocs.io
.. _GitHub: https://github.com/mdomke/schwifty
.. _PyPI: https://pypi.org/project/schwifty
