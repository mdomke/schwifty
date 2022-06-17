.. _changelog:

Changelog
=========

Versions follow `CalVer <http://www.calver.org/>`_ with the scheme ``YY.0M.Micro``.

`2022.06.0`_ - 2022/06/06
-------------------------

Added
~~~~~
* Manually curated list of Bulgarian BICs `@Krystofee <https://github.com/Krystofee>`_
* Manually curated list of Saudi Arabian BICs `@samizaman <https://github.com/samizaman>`_
* Support for `PyInstaller <https://pyinstaller.org/en/stable/>`_ `@Lukasz87 <https://github.com/Lukasz87>`_

Internal
~~~~~~~~
* Run tests on Python 3.10 `@adamchainz <https://github.com/adamchainz>`_
* Use standard keys in ``setup.cfg`` `@adamchainz <https://github.com/adamchainz>`_
* Don't rely on ``hacking`` in test-setup `@adamchainz <https://github.com/adamchainz>`_

`2022.04.2`_ - 2022/04/29
-------------------------

Changed
~~~~~~~
* Allow getting bank names from IBAN. Previously, you could do ``iban.bic.bank_names[0]``, but since
  a BIC can be associated to multiple bank codes the context of the specific bank is lost and you
  could end up with the wrong bank name. `@jose-reveni <https://github.com/jose-reveni>`_


`2022.04.1`_ - 2022/04/29
-------------------------

Changed
~~~~~~~
* The Italian BBAN checksum algorithm is now also applied for San Marino `@fabienpe <https://github.com/fabienpe>`_

Fixed
~~~~~
* Fix Italian BBAN checksum calculation `#78 <https://github.com/mdomke/schwifty/issues/78>`_
* Fix bank code position in BBAN for Jordan banks `@fabienpe <https://github.com/fabienpe>`_


`2022.04.0`_ - 2022/04/11
-------------------------

Changed
~~~~~~~
* Update bank registry for Austria, Czech Republic, Germany, Spain, Poland and Slovakia.

Fixed
~~~~~
* Removed bogus line from dutch bank registry.
* Loading the bank registry now also works on machines that don't have UTF-8 as their default
  encoding `@imad3v <https://github.com/imad3v>`_


`2022.03.1`_ - 2022/03/05
-------------------------

Added
~~~~~
* Country specifc checksum validation for French banks (based on the work of
  `@sholan <https://github.com/sholan>`_)


`2022.03.0`_ - 2022/03/04
-------------------------

Added
~~~~~
* The :class:`.IBAN` and :class:`.BIC` classes now support the ``__len__`` method to allow a more
  Pythonic calculation of the length.

Changed
~~~~~~~
* Update bank registry for Czech Republic, Spain, Hungary, Poland and Slovakia.


`2022.02.0`_ - 2022/02/15
-------------------------

Added
~~~~~
* N26 BIC for Spain `@brunovila <https://github.com/brunovila>`_
* Manually curated entries for banks from Iceland `@gautinils <https://github.com/gautinils>`_

Changed
~~~~~~~
* Removed manually curated bank entries for Spain since all values were already part of
  the generated registry.
* Updated bank registry for Austria, Belgium, Czech Republic, Germany, Spain, Netherlands and Poland
* Added overwrite for IBAN spec of Czech Republic and France. The branch and account code positions
  are wrongly provided in the official IBAN registry.

`2021.10.2`_ - 2021/10/12
-------------------------

Added
~~~~~
* Added 440 additional bank records for Spain.

`2021.10.1`_ - 2021/10/11
-------------------------

Changed
~~~~~~~
* Use `importlib.resources <https://docs.python.org/3.9/library/importlib.html#module-importlib.resources>`_
  for loading internal registries. This removes the need to have ``setuptools`` installed.
  Thank you `@a-recknagel <https://github.com/a-recknagel>`_ for the idea!

Fixed
~~~~~
* Ensure that Belgian BBAN checksums are always 2 digits long.

`2021.10.0`_ - 2021/10/01
-------------------------

Added
~~~~~
* Added IBAN spec for Sudan (SD).
* Added and extended manually curated bank entries for Turkey, Italy, Israel, Ireland, Spain,
  Switzerland and Denmark `@howorkon <https://github.com/howorkon>`_.

Changed
~~~~~~~
* Updated bank registry for Austria, Belgium, Czech Republic, Germany, Netherlands, Poland,
  Slovenia and Slovakia.

Fixed
~~~~~
* Disallow ``schwifty`` to be installed for Python versions older than 3.7. It was unsupported
  before but is now rejected upon installation with an appropriate error message.
* Austrian bank codes are now consistently left padded with zeros. This fixes the mapping from
  IBAN to BIC for the Austrian federal bank institutes.

`2021.06.1`_ - 2021/06/24
-------------------------

Added
~~~~~
* Enable tool based type checking as described in `PEP-0561`_ by adding the ``py.typed`` marker
  `@jmfederico <https://github.com/jmfederico>`_


`2021.06.0`_ - 2021/06/17
-------------------------

Added
~~~~~
* Added bank registry for Swedish Banks `@jmfederico <https://github.com/jmfederico>`_


`2021.05.2`_ - 2021/05/23
-------------------------

Added
~~~~~
* Country specifc checksum validation for Belgian banks, as well as support for generating the
  checksum when using the :meth:`.IBAN.generate`-method. `@mhemeryck <https://github.com/mhemeryck>`_

`2021.05.1`_ - 2021/05/20
-------------------------

Added
~~~~~
* The IBAN validation now optionally includes the verification of the country specific checksum
  within the BBAN. This currently works for German and Italian banks. For German banks the checksum
  algorithm for the account code is chosen by the bank code. Since there are over 150 bank specific
  algorithms in Germany not all of them are implemented at the moment, but the majority of banks
  should be covered.

Changed
~~~~~~~
* Update bank registry for Germany, Poland, Czech Republic, Austria and Netherlands.

`2021.05.0`_ - 2021/05/02
-------------------------

Added
~~~~~
* Added manually curated list of Lithuanian Banks (e.g Revolut Payments UAB).

`2021.04.0`_ - 2021/04/23
-------------------------

Changed
~~~~~~~
* Added type hints to the entire code base.
* Dropped support for Python 3.6
* Update bank registry for Austria, Poland, Germany, Belgium, Czech Republic, Netherlands, Slovenia
  and Slovakia.

`2021.01.0`_ - 2021/01/20
-------------------------

Changed
~~~~~~~
* Restructure documentation and change theme to `furo <https://pradyunsg.me/furo/>`_.
* Added dedicated exception classes for various validation errors.
* Drop support for Python 2. Only Python 3.6+ will be supported from now on.
* Use PEP 517/518 compliant build setup.

`2020.11.0`_ - 2020/12/02
-------------------------

Changed
~~~~~~~
* Updated IBAN registry and bank registries of Poland, Germany, Austria, Belgium, Netherlands,
  Czech Republic and Slovenia.

Added
~~~~~
* Added generated banks for Slovakia `@petrboros <https://github.com/petrboros>`_.
* Added a test to validate the correctnes of BICs in the registry `@ckoehn <https://github.com/ckoehn>`_.

Fixed
~~~~~
* Fixed encoding for Polish bank registry `@michal-michalak <https://github.com/michal-michalak>`_.

`2020.09.0`_ - 2020/09/07
-------------------------

Changed
~~~~~~~
* Migrated build and test pipelines to GitHub actions.

Added
~~~~~
* Added generated banks for Netherlands `@insensitiveclod <https://github.com/insensitiveclod>`_.
* Added generated banks for Spain.

`2020.08.3`_ - 2020/08/31
-------------------------

Fixed
~~~~~
* Fixed IBAN generation for countries with branch/sort code
* Add generated banks for Spain

`2020.08.2`_ - 2020/08/30
-------------------------

Fixed
~~~~~
* Poland's IBAN spec only has a branch-code but no bank-code
* Fixed listing of supported countries for BIC derivation.
* Fixed bank registry for Hungary.

Changed
~~~~~~~
* Updated bank registry Poland, Belgium and Austria.
* Updated IBAN spec for Sao Tome and Principe

`2020.08.1`_ - 2020/08/28
-------------------------

Added
~~~~~
* New attribute :attr:`.BIC.is_valid` and :attr:`.IBAN.is_valid`.

`2020.08.0`_ - 2020/08/06
-------------------------

Changed
~~~~~~~
* Updated bank registry for Poland.

`2020.05.3`_ - 2020/05/25
-------------------------

Added
~~~~~
* Added banks for France, Switzerland and Great Britain.

`2020.05.2`_ - 2020/05/08
-------------------------

Added
~~~~~
* Added :attr:`.BIC.country` and :attr:`.IBAN.country`.


.. _2022.06.0: https://github.com/mdomke/schwifty/compare/2022.04.2...2022.06.0
.. _2022.04.2: https://github.com/mdomke/schwifty/compare/2022.04.1...2022.04.2
.. _2022.04.1: https://github.com/mdomke/schwifty/compare/2022.04.0...2022.04.1
.. _2022.04.0: https://github.com/mdomke/schwifty/compare/2022.03.1...2022.04.0
.. _2022.03.1: https://github.com/mdomke/schwifty/compare/2022.03.0...2022.03.1
.. _2022.03.0: https://github.com/mdomke/schwifty/compare/2022.02.0...2022.03.0
.. _2022.02.0: https://github.com/mdomke/schwifty/compare/2021.10.2...2022.02.0
.. _2021.10.2: https://github.com/mdomke/schwifty/compare/2021.10.1...2021.10.2
.. _2021.10.1: https://github.com/mdomke/schwifty/compare/2021.10.0...2021.10.1
.. _2021.10.0: https://github.com/mdomke/schwifty/compare/2021.06.1...2021.10.0
.. _2021.06.1: https://github.com/mdomke/schwifty/compare/2021.06.0...2021.06.1
.. _2021.06.0: https://github.com/mdomke/schwifty/compare/2021.05.2...2021.06.0
.. _2021.05.2: https://github.com/mdomke/schwifty/compare/2021.05.1...2021.05.2
.. _2021.05.1: https://github.com/mdomke/schwifty/compare/2021.05.0...2021.05.1
.. _2021.05.0: https://github.com/mdomke/schwifty/compare/2021.04.0...2021.05.0
.. _2021.04.0: https://github.com/mdomke/schwifty/compare/2021.01.0...2021.04.0
.. _2021.01.0: https://github.com/mdomke/schwifty/compare/2020.11.0...2021.01.0
.. _2020.11.0: https://github.com/mdomke/schwifty/compare/2020.09.0...2020.11.0
.. _2020.09.0: https://github.com/mdomke/schwifty/compare/2020.08.3...2020.09.0
.. _2020.08.3: https://github.com/mdomke/schwifty/compare/2020.08.2...2020.08.3
.. _2020.08.2: https://github.com/mdomke/schwifty/compare/2020.08.1...2020.08.2
.. _2020.08.1: https://github.com/mdomke/schwifty/compare/2020.08.0...2020.08.1
.. _2020.08.0: https://github.com/mdomke/schwifty/compare/2020.05.3...2020.08.0
.. _2020.05.3: https://github.com/mdomke/schwifty/compare/2020.05.2...2020.05.3
.. _2020.05.2: https://github.com/mdomke/schwifty/compare/2020.05.1...2020.05.2

.. _PEP-0561: https://www.python.org/dev/peps/pep-0561/#packaging-type-information
