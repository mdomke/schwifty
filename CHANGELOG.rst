.. _changelog:

Changelog
=========

Versions follow `CalVer <http://www.calver.org/>`_ with the scheme ``YY.0M.Micro``.

Unreleased
----------
Added
~~~~~
* Added :attr:`.BIC.bank`, the best ranked bank record of a BIC: the institution that services the
  BIC today, as far as the registry knows, e.g. Banco de Sabadell for ``BSABESBB``, which also
  belongs to the bank codes of 19 banks that merged into it (#113).
* Added :attr:`.BIC.sepa_schemes`, the SEPA schemes that the institution of a BIC takes part in
  (``schwifty.domain.SEPAScheme``): credit transfer, core and business-to-business direct debit,
  and card clearing. They are taken from the SCL directory of the Deutsche Bundesbank, which
  ``scripts/get_scl_directory.py`` downloads, and which lists the payment service providers that
  can be reached through its SEPA clearer (#148).

Changed
~~~~~~~
* :attr:`.BIC.banks`, :attr:`.BIC.domestic_bank_codes`, :attr:`.BIC.bank_names` and
  :attr:`.BIC.bank_short_names` are ordered like the lookups by bank code: active records before
  merged, closed and delisted ones, and primary records first among each of them, instead of
  alphabetically. Records of the same rank are ordered by name and bank code. The deprecated
  ``BIC.bank_name``, ``BIC.bank_short_name`` and ``BIC.country_bank_code``, which return the first
  entry of these lists, change accordingly (#113).
* The French and Monegasque bank registries are generated from REGAFI, the register of the
  Autorité de contrôle prudentiel et de résolution, with BICs from GLEIF's BIC-to-LEI mapping. The
  French registry was maintained by hand and covered 217 bank codes. It now covers all 796 that
  REGAFI lists, among them payment and e-money institutions, finance companies and investment
  firms, and the Monegasque one 17 instead of one. Among an institution's BICs, the ones that the
  SCL directory lists as reachable for SEPA payments are preferred, which gives subsidiaries their
  own BIC instead of the one of their group, e.g. Banque CIC Est (``30087``) resolves to
  ``CMCIFRP1SNV`` instead of ``CMCIFRPP``. 556 bank codes have a BIC. Bank codes that REGAFI no
  longer lists, such as those of Crédit du Nord and Orange Bank, are kept as delisted. The manual
  registry only keeps additional BICs of a bank code, such as the branch BICs of BNP Paribas.
* The Irish and Maltese bank registries are generated from the SCL directory, since their IBANs
  use the bank code of the BIC. This adds 234 Irish bank codes, most of them of credit unions, and
  40 Maltese ones. The manual registries keep the codes that the directory doesn't list, such as
  those of KBC Bank Ireland and Ulster Bank. For other countries, the update script reports the
  BICs of the directory that their registries lack (#148).

Fixed
~~~~~
* The BICs of merged banks resolve to their former bank codes again: ``EQBKCZPP`` of Equa bank
  to the Czech bank code ``6100``, which is now serviced by Raiffeisenbank (``RZBCCZPP``), and
  ``ABANSI2X`` of Abanka and ``SKBASI2X`` of SKB banka to their Slovenian bank codes, which are
  now serviced by OTP banka (``KBMASI2X``). The Czech entry had lost its BIC altogether (#138).
* Added the Portuguese bank code ``5200`` of Caixa de Crédito Agrícola Mútuo de Mafra
  (``CDOTPTP1``) and the Monegasque bank code ``30004`` of BNP Paribas (``BNPAMCM1``) (#138).
* The Norwegian check digit of accounts with the account series ``00``, which is reserved for
  settlement accounts between banks, weights all ten digits like for any other account. It was
  computed from the last four digits of the account number only, which gave a different check
  digit for most bank codes, e.g. ``1204.00.12344`` was rejected and ``IBAN.generate`` returned
  ``1204.00.12343`` (#356).

`2026.11.0`_ - 2026/11/05
-------------------------
Added
~~~~~
* Added ``BIC.canonical``, the canonical form of a BIC: ISO 9362 treats a BIC without branch code
  and the same BIC with the branch code ``XXX`` as identical, so both have the 8-character form as
  canonical form, e.g. ``BIC("REVOGB21XXX").canonical == "REVOGB21"``.
* Added ``BIC.banks``, the bank records of a BIC in the registry. ``BIC.exists``,
  ``BIC.bank_names`` and the other lookups by BIC are based on it.
* Bank codes that are no longer in use are now marked in the registry. ``Bank.status`` is a
  ``schwifty.domain.BankStatus`` of ``active``, ``merged``, ``closed`` or ``delisted``. A merged
  bank code names its successor as ``Bank.successor_bank_code`` where it is known, and takes on the
  name and BIC of the bank that services it today, while the merged bank's own name and BIC are kept
  as ``Bank.legacy_name`` and ``Bank.legacy_bic``. The legacy BIC still resolves, e.g.
  ``BIC("GENODEF1HWR").domestic_bank_codes``. Lookups by bank code prefer active records, then
  merged ones, and only then the primary record among them, so that an active branch wins over a
  retired head office. Closed and delisted banks are still returned, so that an IBAN can be
  identified; check their status before initiating a payment. Account codes of retired banks are
  validated with their own checksum method, and :meth:`.IBAN.random` no longer picks retired bank
  codes.
* Added the German checksum method ``48``, used by seven Volksbanken such as Volksbank
  Raiffeisenbank (bank code ``20190109``). It works like method ``06`` over positions 3 to 8, with
  the check digit at position 9. Account codes for these banks were not checked before (#341)
  `@LuisFigueroaG <https://github.com/LuisFigueroaG>`_.
* Added the German checksum method ``50``, used by four banks such as Edekabank (bank code
  ``20090700``). It works like method ``06`` over positions 1 to 6, with the check digit at position
  7. Account codes without the sub-account ``000`` are shifted three positions to the left and
  checked again. Account codes for these banks were not checked before (#342) `@LuisFigueroaG
  <https://github.com/LuisFigueroaG>`_.
* Added the German checksum methods ``46`` and ``47``, used by Barclays Bank Ireland Frankfurt
  Branch (bank code ``50310400``) and Volksbank Weserbergland (bank code ``27290087``). Both work
  like method ``06``, method ``46`` over positions 3 to 7 with the check digit at position 8 and
  method ``47`` over positions 4 to 8 with the check digit at position 9. Account codes for these
  banks were not checked before (#343) `@LuisFigueroaG <https://github.com/LuisFigueroaG>`_.
* Added the German checksum methods ``40`` and ``44``. Method ``40`` is used by Volksbank Rhein-Ruhr
  (bank code ``35060386``) and Volksbank Rheinböllen (bank code ``56062227``), method ``44`` by DZ
  BANK (bank codes ``30060010``, ``40060000`` and ``57060000``). Both work like method ``06`` with
  the weights 2, 4, 8, 5, 10, 9, 7, 3, 6 instead of 2 to 7: method ``40`` over positions 1 to 9 and
  method ``44`` with the first five weights over positions 5 to 9. Account codes for these banks
  were not checked before (#345) `@LuisFigueroaG <https://github.com/LuisFigueroaG>`_.
* Added the German checksum methods ``41``, ``42`` and ``43``, used by Openbank Deutschland (bank
  code ``25020600``), VR Bank im Enzkreis (bank code ``66661454``) and Volksbank Pforzheim (bank
  code ``66690000``). Method ``41`` works like method ``00``, but leaves out positions 1 to 3 if
  position 4 is a 9. Method ``42`` works like method ``06`` with the weights 2 to 9 over positions 2
  to 9. Method ``43`` is a modulus 10 method with the weights 1 to 9 over positions 1 to 9. Account
  codes for these banks were not checked before (#347) `@LuisFigueroaG
  <https://github.com/LuisFigueroaG>`_.
* Added the German checksum methods ``31`` and ``49``. Method ``31`` is used by ABN AMRO Bank,
  Frankfurt Branch (bank code ``50324000``) and takes the remainder modulo 11 of positions 1 to 9,
  weighted 1 to 9 from left to right, as the check digit. A remainder of 10 makes the account code
  invalid. Method ``49`` is used by Kreissparkasse Steinfurt (bank code ``40351060``), Sparkasse
  Nürnberg (bank code ``76050101``) and Stadt- u. Kreissparkasse Erlangen Höchstadt Herzogenaurach
  (bank code ``76350000``). It checks with method ``00`` first and falls back to method ``01``.
  Account codes for these banks were not checked before (#349) `@LuisFigueroaG
  <https://github.com/LuisFigueroaG>`_.
* Added the German checksum method ``A7``, used by Sparkasse Holstein (bank code ``21352240``),
  Sparkasse Gütersloh-Rietberg-Versmold (bank code ``47850065``) and Rheinhessen Sparkasse (bank
  code ``55350010``). It checks with method ``00`` first and falls back to method ``03``. Account
  codes for these banks were not checked before (#351) `@LuisFigueroaG
  <https://github.com/LuisFigueroaG>`_.

Changed
~~~~~~~
* The BIC of an institution's primary office is always returned in its 8-character form, e.g.
  ``IBAN("DE89370400440532013000").bic`` is now ``COBADEFF`` instead of ``COBADEFFXXX``. ISO 9362
  treats both forms as identical, but the registries stored either of them depending on their
  source, so that ``IBAN.bic`` and ``BIC.from_bank_code`` returned the 11-character form for about
  8,400 bank codes, e.g. in Germany, Switzerland, Poland and the UK, and the 8-character form for
  the others. ``BIC.exists`` and the lookups by BIC now accept both forms, e.g.
  ``BIC("REVOGB21XXX").exists`` is ``True`` although the registry lists ``REVOGB21``.
* Updated the Latvian bank registry from Latvijas Banka's current BIC list. It adds six payment
  service providers such as Indexo Banka (``IDXO``) and xpate (``SIAX``), and renames BlueOrange
  Bank to BlueOr Bank and LPB Bank to Magnetiq Bank. Banks that are no longer on the official list,
  such as PNB Banka (``LATB``), are kept so that existing IBANs still resolve. The update
  script now looks up the renamed spreadsheet on the bank's website instead of using a fixed URL.
* Updated the Dutch bank registry from Betaalvereniging Nederland's current BIC list. It adds ten
  payment service providers such as Qonto (``QNTO``) and Trade Republic (``TRBK``), changes the BIC
  of Lloyds Bank from ``LOYDNL2A`` to ``LOYDNL22``, and renames SNS to ASN Bank. Banks that are no
  longer on the official list, such as Viva Payment Services (``VPAY``), are kept so that existing
  IBANs still resolve. The update script now looks up the spreadsheet on the association's website,
  because the fixed URL redirected to an outdated copy that no longer exists.
* The Austrian bank registry now keeps banks that are no longer listed by the Oesterreichische
  Nationalbank, so that existing IBANs still resolve. 21 bank codes that were dropped since 2020,
  such as Commerzialbank Mattersburg (``19620``) and Sberbank Europe (``74000``), were restored.
* The Belgian bank registry now keeps banks whose codes the National Bank of Belgium has released,
  so that existing IBANs still resolve until a code is assigned to another bank. 39 bank
  codes that were dropped since 2020, such as those of bpost (``873``, ``981`` - ``984``) and the
  former AXA Bank codes of Crelan (``766`` - ``771``, ``807`` - ``816``), were restored.
* Updated the Czech bank registry from the Czech National Bank's current code list, which adds
  Comgate (``8620``) and Banking Circle (``6600``) and the BIC of Partners Banka (``PTBNCZPP``). The
  registry now keeps cancelled bank codes, so that existing IBANs still resolve. 29 codes
  that were cancelled since 2020, such as those of Equa bank (``6100``) and Expobank (``4000``),
  were restored. Codes of merged banks keep the bank's name during the run-off period, in which the
  official list replaces it with a note about where payments are forwarded.
* The Spanish bank registry marks the 310 banks that iban.es lists as deregistered as merged, with
  the successor's bank code where iban.es states it, or as closed, according to the reason of
  their deregistration. Lookups prefer the banks that are still active. Since iban.es lags behind
  in places, the script corrects it where the source is known: Bankia, Banco Popular, Liberbank,
  Banco CEISS and Banco Mare Nostrum are marked as merged, and Revolut Bank (``1583``) as
  active. Codes that lead to one of these successors carry its name and BIC, e.g. Banco Popular
  (``0075``) now resolves to Banco Santander (``BSCHESMM``), which the manual registry did
  before. Banks that
  disappear from iban.es are kept, which restores Revolut Bank (``1583``) and Banco de
  Castilla-La Mancha (``0115``), and banks that iban.es lists twice are only included once.
* Updated the Finnish bank registry from Finance Finland's current list, which adds Northmill Bank
  (``719``). The registry now keeps bank codes that are no longer listed, so that existing IBANs
  still resolve. 21 codes that were removed in January 2026, those of Svenska Handelsbanken (``310``
  - ``319``), Swedbank (``380`` - ``389``) and Viva Payment Services (``798``), were restored.
* Updated the UK bank registry from GLEIF's current BIC-to-LEI mapping. Bank codes whose BICs GLEIF
  no longer maps, such as Swedbank (``SWED``), are now kept, so that existing IBANs still resolve.
* The Croatian bank registry is now generated from the Croatian National Bank's list of payment
  service provider codes, which replaced its list of bank codes in March 2025. This adds Aircash
  (``4501006``). Codes that are no longer listed are now kept, so that existing IBANs still resolve,
  which restores HBOR (``2493003``) and Nova hrvatska banka (``2503007``).
* Updated the Hungarian bank registry from the Magyar Nemzeti Bank's current directory, which adds
  Polgári Bank (``311``) and Banking Circle (``312``). Bank codes that are no longer listed are now
  kept, so that existing IBANs still resolve. Five codes that were removed since 2023,
  such as those of Banco Primus (``187``) and Libra Internet Bank (``296``), were restored.
* The Italian bank registry is now generated from Banca d'Italia's registers of banks, e-money
  institutions and payment institutions, with BICs from GLEIF's BIC-to-LEI mapping. It now covers
  all 465 active institutions instead of 215, and names banks as Banca d'Italia does. Several BICs
  are corrected, e.g. cooperative banks now have their own BIC instead of the one of their central
  institute. Institutions that have ceased since 2008 are included, so that existing IBANs still
  resolve. Their status is taken from the registers: 425 were merged into another institution, e.g.
  Banco di Napoli (``01010``) into Intesa Sanpaolo, or continued under a new bank code, e.g.
  UniCredit, and 418 of them resolve to the name and BIC of the institution that services their bank
  code today, 101 were closed, e.g. by liquidation, and 50 ceased for another reason.
* Updated the Liechtenstein bank registry from the SIX bank master, which adds Celsion Bank
  (``83061``). Banks that are no longer listed, such as RMS Sicherheits-Anstalt (``83053``), are
  now kept, so that existing IBANs still resolve.
* Updated the Swiss bank registry from the SIX bank master, which adds Audax Solutions (``83064``).
  Merged institutes were only kept while SIX lists them as merged, and closed ones not at all. Their
  IIDs are now kept, so that existing IBANs still resolve, which restores 15 IIDs that
  were dropped since 2023, such as those of FlowBank (``83029``) and radicant bank (``83036``).
* ``scripts/get_bank_registry_lt.py`` accepts the path of a manually downloaded copy of the Bank of
  Lithuania's branch list, since lb.lt rejects automated downloads. The script no longer writes an
  empty registry when the download is rejected, and keeps bank codes that are no longer listed.
  It is no longer run by ``scripts/update-all.sh``.
* Updated the Norwegian bank registry from Bits' current BIC table, which adds Lunar Bank (``9603``,
  ``9604``) and assigns the codes of the former Sparebanken Sør, such as ``3000``, to Sparebanken
  Norge (``SPAVNOBB``). Bank codes that are no longer listed are now kept, so that existing IBANs
  still resolve. This keeps the codes of Resurs Bank (``9900`` - ``9903``), which were
  removed now, and restores eight codes that were removed since 2024, such as those of Lea Bank
  (``9791``, ``9792``) and Bluestep Bank (``9615``).
* The Polish bank registry now keeps settlement numbers that are no longer listed by Narodowy Bank
  Polski, so that existing IBANs still resolve. 35 numbers that were removed since 2020,
  such as those of DNB Bank Polska and MUFG Bank, were restored. Numbers of banks that were last
  listed as in liquidation or bankruptcy, such as Mercedes-Benz Bank Polska (``15800006``), are
  marked as closed.
* Updated the Polish bank registry, which adds Trade Republic Bank (``29800010``) and a branch of
  UniCredit (``29100048``), and updates the BICs of several cooperative banks.
* The Romanian bank registry is now generated from GLEIF's BIC-to-LEI mapping, like the UK registry,
  since the website it was scraped from no longer lists the banks. It contains 76 active
  institutions instead of 46 banks from 2022, among them Salt Bank and TechVentures Bank. The
  National Bank, the Treasury and TransFonD, which GLEIF lacks, are maintained in the manual
  registry. Banks that are no longer active, such as OTP Bank Romania and Alpha Bank Romania, are
  kept so that existing IBANs still resolve. The manual entry of Revolut, which GLEIF
  provides as well, is removed.
* The Swedish bank registry is now generated from the CSV table of Bankinfrastruktur i Sverige
  instead of a PDF from 2023, which no longer requires camelot and a separate Docker image. This
  adds eleven IBAN IDs, such as those of Revolut (``215``), Trade Republic (``216``) and Lunar
  Bank (``971``), and updates several BICs and names, e.g. Svea Bank's BIC is now ``SVEASESS``.
  IBAN IDs with several BICs, such as Steven AB's, keep all of them. IBAN IDs that are no longer
  listed are now kept, so that existing IBANs still resolve.
* The Slovenian bank registry now also keeps the codes of the former Abanka (``06``) as aliases of
  OTP banka, and restores 38 codes of Abanka and Nova KBM that were dropped in 2021. Codes of other
  institutes that are no longer listed are now kept as well, so that existing IBANs still resolve.
* The Slovak bank registry is now generated from the current list of the Národná banka Slovenska.
  The file the script downloaded had not been updated since 2022. This adds four banks, such as Air
  Bank (``3030``) and Partners Banka (``6363``), and renames Privatbanka to Penta Bank. Codes that
  are no longer listed are now kept, so that existing IBANs still resolve, and codes of
  merged banks keep the bank's name during the run-off period, e.g. 365.bank (``6500``).
* Updated the Ukrainian bank registry from the National Bank of Ukraine. The update script no longer
  worked with current versions of pandas, so the registry had not been updated since 2023. Banks in
  liquidation, which the National Bank still lists, are now included, and banks that are no longer
  listed at all are kept, so that existing IBANs still resolve. This adds 56 bank codes,
  among them nine that were dropped before, such as the one of Bank Forward (``380418``).
* The Estonian bank registry is now generated from the list of the Estonian Banking Association.
  It was created in 2022 by querying a third-party IBAN validator and had not been updated since.
  This adds Luminor Bank (``96``, ``17``), OP Corporate Bank (``51``) and other payment service
  providers, corrects the BIC of Wallester (``WALLEE22``), and assigns the codes ``11`` and ``55``
  to Monemon and Crowdestate instead of Swedbank and Versobank. Codes that are no longer listed,
  such as the one of Danske Bank (``33``), are kept so that existing IBANs still resolve.
* The Georgian bank registry is now generated from the National Bank of Georgia's list of IBAN
  codes. It was created in 2022 by querying a third-party IBAN validator and had not been updated
  since. This adds the State Treasury (``TR``) and five banks, such as Paysera Bank Georgia
  (``PS``). Codes that are no longer listed, such as the one of Capital Bank (``IN``), are kept so
  that existing IBANs still resolve.
* The Moldovan bank registry now contains all participants of the payment system that the National
  Bank of Moldova lists, such as the State Treasury (``TR``) and Moldcell (``MC``), in a single
  manually maintained registry. Comerţbank is now found by its code ``CM`` instead of ``CB``.
* Completed the names of ten Bosnian banks that were cut off, e.g. ``NLB BANKA D`` is now
  ``NLB Banka d.d., Sarajevo``, and ``Hypo Alpe`` and ``Sberbank a`` now carry their current names
  Addiko Bank and Atos bank.
* The Bosnian banks Vakufska banka (``160``) and Banka Srpske (``568``) are marked as delisted and
  closed, and ASA Banka Naša i Snažna (``140``) as merged into ASA Banka (``134``).
* Updated the Serbian bank registry according to GLEIF: AIK Banka, Mobi Banka and Expobank carry
  their current names AikBank, Yettel Bank and Adriatic Bank, three cut-off names are completed,
  six banks that GLEIF lists as inactive, such as Vojvođanska banka (``355``), are marked as
  delisted, and Jugobanka (``365``) as closed. The entry of British American Tobacco under the code
  ``000`` is removed.
* Added Banka Poštanska štedionica (``200``), NLB Banka (``205``), OTP banka Srbija (``325``),
  3 Banka (``370``) and the National Bank of Serbia (``908``) to the Serbian bank registry, which
  lacked them although they are on the National Bank of Serbia's list of banks. Alpha Bank Srbija
  (``180``), Crédit Agricole Srbija (``330``) and mts banka (``360``), which are no longer on that
  list, are marked as merged into AikBank, Raiffeisen banka and Banka Poštanska štedionica, whose
  names and BICs they now resolve to. So are Eurobank Direktna (``250``), which merged into AikBank
  in 2025, and Direktna Banka (``150``), which had merged into Eurobank Direktna before.
* Updated the names of Danish banks that were renamed or merged, according to the legal names that
  GLEIF lists for their BICs, e.g. Nordea Bank Danmark is now Nordea Danmark, Filial af Nordea
  Bank Abp, Finland, Sparekassen Sjælland-Fyn is now SJF Bank, and Sydbank is now AL Sydbank.
* Removed 104 entries from the manual Italian registry that duplicate the generated one, or
  contradict it with outdated data. Italian banks now resolve to their current BIC, e.g. Fineco
  (``FEBIITM2``) and Isybank (``ISYBITMM``), and banks that have ceased, such as Banca Popolare
  di Vicenza, are no longer reported as active. The manual registry keeps the entries that add a
  BIC the generated registry lacks.
* Removed six entries from the manual UK registry that GLEIF provides as well, such as Barclays
  Bank UK (``BUKB``) and ClearBank (``CLRB``). The duplicate entry of Revolut Ltd is removed as
  well, Bilderlings Pay (``BIYS``) resolves to its BIC ``BIYSGB2A``,
  and ePayments Systems (``EPMT``) is marked as closed, since it has been in special
  administration since October 2026.
* German bank codes of merged banks now resolve to the successor bank, e.g. ``13061088``
  (Raiffeisenbank Wismar) to Volks- und Raiffeisenbank, while account codes are still checked with
  the checksum method of the original bank. This applies as soon as the Bundesbank announces the
  deletion of a bank code together with a successor. Bank codes that the Bundesbank has deleted are
  no longer dropped from the registry: merged ones are kept as aliases of their successor, and those
  without a successor, such as Greensill Bank (``29020200``), as delisted banks if their checksum
  method is known. 151 bank codes are kept this way, 36 of them merged. The names of retired bank
  codes no longer carry the suffix "-alt-" ("old"), which the Bundesbank adds to the names of codes
  that a merger made obsolete, e.g. Raiffeisenbank Wismar.
* Banks that are kept in the Austrian, Belgian, Croatian, Czech, Estonian, Finnish, Georgian,
  German, Hungarian, Italian, Latvian, Liechtenstein, Dutch, Norwegian, Polish, Romanian, Slovak,
  Slovenian, Spanish, Swedish, Swiss, UK and Ukrainian registries although they are no longer on the
  official list are marked as delisted, or as merged or closed where the source says so, so that
  lookups prefer the banks that are still listed. Codes of merged banks that lead to a successor,
  such as the Swiss and Slovenian ones, name the successor's bank code and the name they were last
  listed under.

Fixed
~~~~~
* ``IBAN.bank`` and ``IBAN.bic`` always describe the same institution. They used to pick their
  record differently when a bank code has several, so that e.g. the name of Revolut Bank UK came
  with the BIC of Revolut Ltd, which share the UK bank code ``REVO``. All lookups by bank code now
  rank the records by status, then by how generic their BIC is, then by ``primary``. This changes
  ``IBAN.bank`` for about 130 bank codes, and the order of ``BIC.candidates_from_bank_code``, whose
  first candidate is now the BIC that ``BIC.from_bank_code`` returns. Equivalent forms of a BIC rank
  equally and are listed only once. The UK bank code ``REVO`` now resolves to Revolut Bank UK, which
  holds Revolut's UK accounts since 2026, instead of Revolut Ltd.
* ``BIC`` no longer rejects BICs of banks in Kosovo (e.g. ``RBKOXKPR``) with
  ``InvalidCountryCode``. SWIFT assigns them the code ``XK``, which is not part of ISO 3166-1 and
  therefore unknown to ``pycountry``, although ``IBAN`` already accepts it.
  (#346) `@ryanduguid <https://github.com/ryanduguid>`_.
* The registry update scripts no longer truncate the generated registry file when downloading or
  processing the source data fails. The output is now written to a temporary file that replaces
  the previous registry only once it has been written completely.
* Bank codes in the Austrian and Swiss registries carry their own primary flag again. Bank codes
  that share a BIC and name were grouped together and all took the flag of the first one. This
  marked 241 Austrian branch codes as primary and 86 head office codes as non-primary, and 212
  Swiss head office IIDs as non-primary.
* The German checksum method ``76`` (used by Commerzbank vormals Dresdner Bank) no longer accepts a
  check digit of 0 when the weighted sum leaves a remainder of 10 (e.g. ``0000005000``). The
  remainder is the check digit itself, so there is none for a remainder of 10 and, according to the
  Bundesbank specification, the account code cannot be checked. Account codes starting with ``00``
  are still checked without the sub-account number, with the check digit at position 10 (e.g.
  ``0000005009``) (#350) `@LuisFigueroaG <https://github.com/LuisFigueroaG>`_.
* The German checksum method ``13`` (used by Commerzbank) now also accepts account numbers whose
  sub-account number ``00`` was left out and that were padded with leading zeros instead (e.g.
  ``0001234566``), as the Bundesbank specification recommends (#352) `@wavebyrd
  <https://github.com/wavebyrd>`_.
* The national check digits of Kosovo (``XK``) IBANs are now validated with ISO 7064 mod 97-10, as
  specified by the Central Bank of Kosovo and already done for Bosnia and Herzegovina, Montenegro,
  North Macedonia and Serbia. The last two digits of the BBAN used to be read as part of the account
  code, so ``validate_bban=True`` accepted wrong check digits without a warning (e.g. ``XK75 1212
  0123 4567 8907``). :attr:`.IBAN.account_code` is now the 10-digit client number and the check
  digits are available as :attr:`.IBAN.national_checksum_digits`. :meth:`.IBAN.generate` now
  computes them as well (#354) `@Enesuygurs <https://github.com/Enesuygurs>`_.

`2026.10.1`_ - 2026/10/25
-------------------------
Added
~~~~~
* Added :attr:`.IBAN.is_aspirational` and :attr:`.BBAN.is_aspirational` to tell whether a
  country's IBAN format is only reserved and not yet part of the official IBAN registry (#248).
* Added a generated bank registry for the United Kingdom, built from GLEIF's monthly BIC-to-LEI
  mapping. It contains about 2,700 head-office BICs for more than 2,300 bank codes, compared to
  the 50 manually maintained entries before. The manual registry now only holds the entries GLEIF
  lacks and pins the preferred BIC where GLEIF lists several for one bank code.
* Added the German checksum method ``C1``, used by ING-DiBa (bank code ``50010517``). Account
  codes starting with ``5`` are checked with a variant of method ``17`` over positions 1 to 9,
  all others with method ``17`` itself. Account codes for this bank were not checked before
  (#334) `@LuisFigueroaG <https://github.com/LuisFigueroaG>`_.
* Added the German checksum method ``C0``, used by ten savings banks such as Sparkasse
  Vorpommern auf Rügen (bank code ``13051042``). Account codes with exactly two leading zeros are
  checked with method ``52``, which also takes the bank code into account, and with method ``20``
  if that fails. All other account codes are checked with method ``20`` only (#337)
  `@LuisFigueroaG <https://github.com/LuisFigueroaG>`_.
* ``scripts/get_iban_registry.py`` accepts the path of a manually downloaded "IBAN Registry (TXT)"
  file, since swift.com rejects automated downloads. The script also no longer truncates
  ``generated.json`` when the download or parsing fails.

Changed
~~~~~~~
* Updated the IBAN registry from the latest SWIFT release. Honduras (HN) and Yemen (YE) are now
  part of the official registry and no longer flagged as aspirational. Iceland (IS) is now in the
  SEPA zone, and the BBAN structure of Brazil is now more liberal. The Czech and Estonian
  structures are kept at their previous, more detailed form in ``overwrite.json``.
* The bank registry is now loaded per country on first use instead of all at once, and the
  ``Bank`` objects are shared between the lookup indexes and use ``__slots__``. A first lookup of
  a German IBAN now adds about 3 MB of memory instead of 26 MB, and a French one less than 1 MB
  (#246). Thanks to `@UnknownPlatypus <https://github.com/UnknownPlatypus>`_ for the analysis.
* A BIC lookup (e.g. ``BIC.domestic_bank_codes`` or ``BIC.bank_names``) only searches the bank
  registry of the BIC's own country. Foreign-based banks listed in another country's registry,
  such as Commerzbank (``COBADEFF``) with its Swiss bank codes, are no longer returned for their
  BIC. This also fixes ``BIC("REVOFRP2XXX").domestic_bank_codes`` returning the Lithuanian
  ``32501`` instead of the French ``28233`` (#242).

Fixed
~~~~~
* Fixed a typo in the JSON schema pattern that pydantic generates for ``BIC`` fields: the
  optional branch location used ``(:?`` instead of ``(?:``, so published schemas accepted
  strings containing a colon (e.g. ``GENODEM1:GLS``) that the actual validation rejects (#338)
  `@feiiiiii5 <https://github.com/feiiiiii5>`_.
* The supported-country lists of ``BIC.from_bank_code`` and ``BIC.candidates_from_bank_code`` no
  longer mention South Africa, which has no bank registry data and always raised
  ``InvalidBankCode``, and now include Georgia, Malta, Montenegro and Pakistan, which do have
  registry data. The documentation's BIC validation example claimed an ``InvalidStructure`` error
  for a 12-character input that actually raises ``InvalidLength`` (#339)
  `@feiiiiii5 <https://github.com/feiiiiii5>`_.
* ``BBAN.random`` and ``IBAN.random`` called with a ``bank_code`` now solve the national check
  digit for the checksum method of that bank, which is the one the result is validated against,
  instead of the method of a randomly picked bank. For German banks whose method rarely accepts
  an account code built for another method (e.g. Deutsche Bank, method ``63``) generation could
  run out of retries and raise ``GenerateRandomOverflowError``. The bank is now looked up the same
  way validation does, even with ``use_registry=False``. Since no random bank is drawn anymore
  when the bank code is given, the output for a seeded ``random`` changes in every country (e.g.
  ``BBAN.random("FR", random=Random(1), bank_code="11425")``) (#329)
  `@LuisFigueroaG <https://github.com/LuisFigueroaG>`_.
* Corrected UK bank code lookups: ``BOFS`` now resolves to Bank of Scotland (``BOFSGB21``)
  instead of Lloyds, ``DABA`` to Northern Bank (``DABAGB2B``) instead of one of its branches, and
  Halifax, Co-operative Bank, TSB, PayrNet, Paysend, Clear Junction and The Currency Cloud to
  their current head-office BICs instead of branch, passive or retired ones. The German
  ``DEUTDEFFXXX`` was removed from the UK registry.
* The German checksum method ``76`` (used by Commerzbank vormals Dresdner Bank) now accepts
  account numbers whose sub-account number ``00`` was left out and that were padded with leading
  zeros instead, so the check digit sits at position 10 (e.g. ``0000123456``), as the Bundesbank
  specification requires (#330) `@wavebyrd <https://github.com/wavebyrd>`_.
* The Swiss bank registry now includes the foreign-based banks that take part in Swiss payments
  (e.g. Deutsche Bank AG, Commerzbank AG, Citibank N.A., Sparkasse Hochrhein), so Swiss IBANs
  with their bank codes resolve to a bank and BIC. The generator used to drop every bank that
  is not domiciled in Switzerland.
* The Belgian bank registry no longer lists the identification numbers that the National Bank of
  Belgium marks as unassigned (``VRIJ``) or unavailable (``Onbeschikbaar``) as banks of that
  name. Since the switch to the new NBB list their ``N/A`` BIC was read as empty, so the
  generator kept them, e.g. ``BE68 5390 0754 7034`` resolved to a bank called
  ``Onbeschikbaar`` and ``IBAN.random("BE")`` could pick those codes (#335)
  `@raams95 <https://github.com/raams95>`_.

Internal
~~~~~~~~
* Added 115 tests covering the national checksum algorithms, registry helpers and IBAN/BBAN/BIC
  edge cases (#333) `@wxs-lang <https://github.com/wxs-lang>`_.

`2026.10.0`_ - 2026/10/19
-------------------------
Added
~~~~~
* Added the German checksum method ``95``, used by UniCredit Bank - HypoVereinsbank (bank code
  ``70020270``). It computes like method ``06``, but treats the account ranges the Bundesbank
  exempts from the check digit as valid. Account codes for this bank were not checked before.
* Added the German checksum methods ``A2`` and ``A3``. Both check the account number with
  method ``00`` first and fall back to method ``04`` (``A2``) or ``10`` (``A3``). Banks using
  them (e.g. Nassauische Sparkasse, Sparkasse Hannover) previously had their national check
  digit silently accepted without being verified.
* Added e-money institutions and banks that were missing from the bank registries: OpenPayd
  (MT — first Maltese registry), ClearBank and Bilderlings Pay (GB), Score and Secure Payment
  and Deblock (FR), bunq, Pecunia Cards and Financière des Paiements Électroniques (ES),
  Unlimit (CY), MyFin (BG), Revolut Bank (PT), Enpara Bank (TR), United Bank and Allied Bank
  (PK — first Pakistani registry), and the BIC for PrivatBank (UA).

Changed
~~~~~~~
* ``validate_bban=True`` now emits a ``NationalChecksumNotVerified`` warning when the country's
  BBAN specification declares national check digits but no algorithm is registered to verify them
  (35 of the 54 countries that declare check digits, e.g. ``HU`` and ``SE``, which silently passed
  before, #310). The digits are still accepted, since a missing algorithm must not reject an
  otherwise valid IBAN, but the pass is no longer silent. Turn the warning into an error with
  ``warnings.simplefilter("error", NationalChecksumNotVerified)`` to make the missing check fail
  instead.
* Removed support for deprecated Python version 3.10
* Use Python 3.15 by default and in CI, with compatible Pydantic dependencies.
* Registry generation scripts now use ``httpx2`` instead of ``requests`` for HTTP downloads.
* Simplified internal registry caching, character lookups, checksum helpers, and validation routines
  for improved efficiency and cleaner code structure while preserving exact behavior.
* Simplified the IBAN checksum validation. The redundant ``self.numeric % 97 == 1`` test has
  been dropped in favour of the stricter canonical ``ISO7064_mod97_10`` comparison, which it
  always implied. Behaviour is unchanged.
* Updated the bank registries for Germany, Austria, Belgium and Poland.

Fixed
~~~~~
* Registry update scripts report a missing download link instead of an attribute or lookup error.
* Validating a pydantic model whose ``BIC`` field is not a string now reports a
  ``bic_format`` field error instead of letting the ``TypeError`` from ``BIC()`` escape,
  which is what the ``IBAN`` validator in the same library already does.
* The German checksum method ``63`` (used by Deutsche Bank) now accepts account numbers whose
  sub-account number ``00`` was left out and that were padded with leading zeros instead, so the
  check digit sits at position 10 (e.g. ``0001234566``), as the Bundesbank specification requires.
* ``IBAN.from_bban`` now normalizes whitespace and case before computing the checksum, matching
  the text constructors. Grouped BBANs and lowercase country codes no longer raise a raw
  ``KeyError`` during checksum calculation.
* The German checksum method ``99`` now accepts every account number from ``0396000000`` to
  ``0499999999`` without a check, as the Bundesbank specification requires. Previously only the
  two range boundaries were exempt, so valid account numbers in between (e.g. at UniCredit Bank -
  HypoVereinsbank) could be rejected.
* Added the Cypriot BIC ``OROACY2LXXX`` (ORO PAY LTD) to the manual registry (#297).
* Eight-character BICs now fall back to their equivalent ``XXX`` registry entry for
  bank codes and names when an exact entry is absent. Exact matches still take priority.
* Eleven-character BICs now fall back to the eight-character institution entry when the
  registry holds no branch-specific record. An 11-character BIC denotes a branch of the
  institution its first eight characters identify, but not every national registry lists
  entries per branch (#112).
* ``IBAN.bank`` (and with it ``IBAN.bank_name`` and ``IBAN.bank_short_name``) now
  resolve a bank code to the registry record flagged ``primary`` instead of whichever
  record happened to be read first. National registries list one record per branch, so
  the two could name a different institution than ``IBAN.bic`` does.
* ``BIC.from_bank_code`` now prefers BICs the registry marks as primary when a bank code
  maps to several equally generic BICs, before falling back to the alphabetical tie-break.
  For the French bank code 18719 this is the head office ``BFCORERXXXX`` rather than the
  Mayotte branch ``BFCOYTYTXXX``, which is no longer flagged primary. The German bank code
  48020151 now resolves to ``HAUKDEFFXXX``, the entry the Bundesbank file marks as the bank
  code's primary record, instead of the secondary ``LAMPDEDDXXX``.
* Updated the Slovenian bank registry, which could no longer be generated because Banka
  Slovenije moved its list of payment service provider identifiers. Bank codes added since
  the last update (e.g. ``02188``, NLB) now resolve, names keep their Slovenian characters,
  and the retired codes of SKB banka and Abanka are kept as aliases of OTP banka so IBANs
  still in circulation continue to resolve.
* Deep-copying an IBAN or BIC created with ``allow_invalid=True`` no longer raises a
  validation error. The copy preserves the original value and validation status.
* ``BBAN.validate_national_checksum`` no longer raises an ``AssertionError`` (or an
  ``IndexError`` under ``python -O``) for a BBAN shorter than the country spec; it now
  raises ``InvalidAccountCode``, as the other national methods already do.
* The German checksum methods that inspect the account code themselves (08, 63, 68, 76, 88 and 99)
  now also raise ``InvalidAccountCode`` for a BBAN that is too short to carry an account code,
  instead of leaking a raw ``ValueError`` or ``IndexError`` that ``except SchwiftyException``
  does not catch.
* Updated the Swiss bank registry, which could no longer be generated since SIX started
  emitting bank master records without a BIC. Retired IIDs of merged institutes (e.g. the
  former Credit Suisse codes, now UBS) are now kept as aliases of their successor, so IBANs
  still in circulation keep resolving.
* ``IBAN.generate`` and ``BBAN.random`` now work for countries whose BBAN specification has no
  component positions (e.g. aspirational countries like Comoros or Burkina Faso), via the new
  ``IBANSpec.has_positions`` check.

`2026.07.3`_ - 2026/07/23
-------------------------
Changed
~~~~~~~
* ``BBAN.random`` now constructs a valid national checksum instead of repeatedly
  generating random BBANs until one happens to validate. Each checksum algorithm can now
  ``solve`` the components it is responsible for: the German methods splice a valid check
  digit into the account code, Iceland fixes its embedded check digit, and the Czech and
  Slovak methods adjust the account and branch codes to satisfy their mod-11 constraints.
  As a result random BBANs are produced on the first attempt for effectively every
  country and bank, rather than after up to 2000 brute-force retries.

`2026.07.2`_ - 2026/07/22
-------------------------
Changed
~~~~~~~
* Refactored internal registry deserialization to construct and return strongly typed domain
  objects (``IBANSpec`` and ``Bank``) instead of raw dictionaries. ``Bank`` now also carries the
  ``checksum_algo`` field that selects the national checksum method.
* Added a dictionary-compatibility mixin to ``IBANSpec`` and ``Bank``, supporting subscription
  and ``get()`` lookups, to maintain backward compatibility for public attributes
  like ``IBAN.spec`` and ``IBAN.bank``.

Deprecated
~~~~~~~~~~
* Dict-style access (subscription and ``.get()``) on the objects returned by ``IBAN.spec`` /
  ``IBAN.bank`` (and their ``BBAN`` counterparts) is deprecated and now emits a
  ``DeprecationWarning``. Use attribute access instead, e.g. ``bank.name`` instead of
  ``bank["name"]``.

Removed
~~~~~~~
* Removed the untyped, undocumented registry helpers ``schwifty.registry.get``,
  ``schwifty.registry.has`` and ``schwifty.registry.save``. These were never part of the
  advertised public interface, but if you relied on them, use the typed query functions instead:
  ``get_iban_spec``, ``get_banks_by_country``, ``get_banks_by_code``, ``get_banks_by_bic``,
  ``get_countries`` and the new ``get_all_banks``.

Fixed
~~~~~
* The country-specific German checksum was silently skipped when validating a BBAN with
  ``validate_bban=True``. The per-bank ``checksum_algo`` was dropped during the switch to typed
  registry objects, so ``BBAN.validate_national_checksum`` always resolved to a non-existent
  ``DE:default`` algorithm and returned successfully without checking. The account-code checksum
  is now validated again for German banks.
* German checksum method 11 rejected valid account numbers whose check digit is
  ``0``. ``Algorithm11.reconcile`` returned the raw value ``11`` for these
  accounts instead of mapping it to ``0`` like the base method 06/10 do, so
  ``validate`` compared against the impossible two-digit check digit ``"11"``
  `@chuenchen309 <https://github.com/chuenchen309>`_.
* Validate the whole BIC string when checking its structure. Previously the
  check was only anchored at the start, so an 11-character BIC with
  non-alphanumeric characters in the branch code (e.g. ``GENODEM1@#%``) was
  accepted and even exposed the garbage through ``BIC.branch_code``
  `@gaoflow <https://github.com/gaoflow>`_.
* Fixed the German checksum method ``16``. It was computed over account
  positions ``6-9`` (copied from method ``15``), but per the Bundesbank
  specification method ``16`` is computed like method ``06`` over positions
  ``1-9``; only method ``15`` is restricted to positions ``6-9``. Valid IBANs
  for banks using method ``16`` (e.g. Hanseatic Bank) were wrongly rejected.
* Fixed the German checksum method ``08`` threshold. Per the Bundesbank
  specification the check digit is only applied from account number ``60000``
  upward, but the threshold was set to ``6000``. Accounts in the
  ``[6000, 60000)`` range for banks using method ``08`` (e.g. NRW.BANK,
  Helaba) were wrongly rejected.
  `@chuenchen309 <https://github.com/chuenchen309>`_.


`2026.07.1`_ - 2026/07/06
-------------------------
Fixed
~~~~~
* Reverted changes to Italian bank registry due to invalid bank codes being added.


`2026.07.0`_ - 2026/07/02
-------------------------
Added
~~~~~
* Added Yemen (``YE``) to the IBAN registry so Yemeni IBANs can be parsed and
  validated (#294) `@CedricConday <https://github.com/CedricConday>`_.

Fixed
~~~~~
* Registered the ISO 7064 mod 97-10 national checksum algorithm for Bosnia and
  Herzegovina (``BA``) instead of ``BT`` (Bhutan, which has no IBAN), so the
  national checksum of ``BA`` IBANs is now validated (#264) `@CedricConday <https://github.com/CedricConday>`_.
* Fix BBAN pickle and deepcopy failures `@gaoflow <https://github.com/gaoflow>`_.
* Return ``True`` from ``validate_national_checksum`` on success `@gaoflow <https://github.com/gaoflow>`_.

Updated
~~~~~~~
* Update bank registries for Germany, Italy and Poland.


`2026.03.0`_ - 2026/03/04
-------------------------
Added
~~~~~
* Added bank registry for Moldova (MD) with 10 commercial banks.
* Extended bank registries for Great Britain, Spain and Romania.
* Added Revolut and Trade Republic to Spanish bank registry.

Changed
~~~~~~~
* Updated bank registries and updated them to format v2 for Switzerland, Poland,
  Austria and Finnland.
  The v2-format groups entries that have the same name and BIC and aggregates the
  matching bank codes. This reduces the file-size by up to 75%.

Internal
~~~~~~~~
* Update tooling and switch to PEP-735 compliant dependency groups.
* Use `uv` to manage Python versions instead of `flox`.


`2026.01.0`_ - 2026/01/23
-------------------------
Changed
~~~~~~~
* Removed support for deprecated Python version 3.9
* Updated local bank registries

Added
~~~~~
* Adding Revolut Bank UAB `@bitshift <https://github.com/bitshift>`_.

Fixed
~~~~~
* Fix Modulr Finance `@bitshift <https://github.com/bitshift>`_.


`2025.09.0`_ - 2025/09/22
-------------------------
Added
~~~~~
* Added bank registry for Liechtenstein.

Fixed
~~~~~
* The Polish IBAN format override was breaking down the bank code in an unusual way, which made it
  hard to generate IBANs from the components known to the user. This has been detected and fixed
  by `@pywkm <https://github.com/pywkm>`_.


`2025.07.0`_ - 2025/07/28
-------------------------
Changed
~~~~~~~
* Allow lax validation of ``IBAN`` values when used with Pydantic

  .. code-block:: python

    from typing import Annotated
    from typing import Field
    from pydantic import BaseModel


    class Model(BaseModel):
      iban: Annotated[IBAN, Field(strict=False)]

* Updated bank registry for Germany, Autstria, Switzerland and Poland.

Fixed
~~~~~
* Fixed script populating the Italian bank registry, adding over 150 additional banks (thanks to `@ciotto <https://github.com/ciotto>`_)


`2025.06.0`_ - 2025/06/25
-------------------------
Changed
~~~~~~~
* Allow country specific components to be passed to ``IBAN.generate()``.

  .. code-block:: pycon

    >>> IBAN.generate("IS", bank_code="0101", account_type="26", account_code="85002", account_holder_id="5402696029")
    <IBAN=IS910101260850025402696029>

`2025.01.0`_ - 2025/01/21
-------------------------
Changed
~~~~~~~
* Update the bank registries for Austria, Germany and Switzerland
* Added some manual entries for France and Great Britain

`2024.11.0`_ - 2024/11/11
-------------------------
Changed
~~~~~~~
* Removed support for deprecated Python version 3.8
* Updated the bank registries for Austria, Germany, Poland, Netherlands, Spain, Czech Republic,
  Italy, and Switzerland.

Added
~~~~~
* New French Banks `@Natim <https://github.com/Natim>`_
* Add modulr bank to Spanish bank registry `@jose-reveni <https://github.com/jose-reveni>`_

`2024.09.0`_ - 2024/09/31
-------------------------
Fixed
~~~~~
* Fix Python 3.8 support while it is still supported (EOL is 2024-10) (thanks to `@bwoodsend <https://github.com/bwoodsend>`_)

`2024.08.1`_ - 2024/08/13
-------------------------
Added
~~~~~
* Allow ``BIC`` and ``IBAN`` objects to be deepcopied (thanks to `@binaryDiv <https://github.com/binaryDiv>`_
  for pointing this out).

`2024.08.0`_ - 2024/08/13
-------------------------
Added
~~~~~
* Added French Polynesian banks to the registry `@tut-tuuut <https://github.com/tut-tuuut>`_
* Added bnext to the Spanish registry `@jose-reveni <https://github.com/jose-reveni>`_

Changed
~~~~~~~
* Extended the Danish bank registry including many more banks now.
* Updated the Belgian bank registry `@sennbos <https://github.com/sennebos>`_
* Updated bank registries for Austria, Germany, Poland, Czech Republic, Switzerland, Italy, Norway
  and Netherlands.

`2024.06.1`_ - 2024/06/10
-------------------------
Fixed
~~~~~
* The ``BIC.from_bank_code`` now handles banks correctly that have no value for the BIC field in the
  registry.

Changed
~~~~~~~
* Use ``hatch fmt`` and ``hatch test`` commands for internal development.

`2024.06.0`_ - 2024/06/04
-------------------------
Changed
~~~~~~~
* Stop using the "elfprooef" algorithm when validating Dutch IBANs, since the administrative
  authority says it should not be checked any more.

`2024.05.4`_ - 2024/05/25
-------------------------
Added
~~~~~
* The ``IBAN`` and ``BBAN`` classes now have an additional property ``currency_code`` for countries
  like Seychelles, Guatemala or Mauritius.

Fixed
~~~~~
* Also allow the BIC lookup for non-primary banks. For countries like Switzerland the lookup did
  fail for banks which did not have the primary-flag set, even though an appropriate mapping was
  available.
* ``IBAN.random()`` now also works for countries which have a currency code included in their BBAN
  e.g. Mauritius or Seychelles.
* ``IBAN.random()`` now also works for aspirational countries, where no information of the BBAN
  structure is available, e.g. Comoros.

`2024.05.3`_ - 2024/05/10
-------------------------
Added
~~~~~
* There is a new classmethod ``IBAN.random()`` that allows you to create random, but valid IBANs.

  .. code-block:: pycon

    >>> IBAN.random()
    <IBAN=LT435012771675726758>

  You can narrow down the generated values by providing the corresponding parameters to this
  function. E.g. to get only Spanish IBANs you can do

  .. code-block:: pycon

    >>> IBAN.random(country_code="ES")
    <IBAN=ES8801253179194914182449>

Changed
~~~~~~~
* Some missing bank associations have been added to the Portoguese bank registry by
  `@tiagoafseixas <https://github.com/tiagoafseixas>`_

`2024.05.2`_ - 2024/05/09
-------------------------
Fixed
~~~~~
* Add `typing-extensions` as explicit dependency for Python < 3.11 to support the `Self` type.

`2024.05.1`_ - 2024/05/09
-------------------------
Changed
~~~~~~~
* Remove custom collection logic of the bank registry for ``pyinstaller``. The changes introduced in
  `#92 <https://github.com/mdomke/schwifty/pull/92>`_ were wrong and have been reverted. Usage
  example

  .. code-block:: bash

    $ pyinstaller <script> --collect-data schwifty --copy-metadata schwifty

`2024.05.0`_ - 2024/05/07
-------------------------
Fixed
~~~~~
* Loading JSON data into a Pydantic model with an ``IBAN`` or ``BIC``-field
  (``Model.model_validate_json()``) was previously broken and has been fixed now.

Added
~~~~~
* JSON schema generation for Pydantic models.

Changed
~~~~~~~
* Updated bank registries.
* Remove the dependency to ``iso3166`` since its functionallity is already covered by ``pycountry``


`2024.04.0`_ - 2024/04/18
-------------------------
Added
~~~~~
* Added Revolut Bank for Spain `@brunovilla <https://github.com/brunovila>`_
* Added support for Python 3.12
* Added manually curated bank registry for Montenegro `@Djuka <https://github.com/Djuka>`_

Changed
~~~~~~~
* The bank registry is now internally validated, so that all domestic bank codes actaully match the
  specification of the corresponding BBAN structure. As a result some entries had to be removed,
  because they did contain invalid bank codes.
* The Danish national checksum algorithm is considered opaque and the checksum digit is assumed to
  be part of the account number (which is now always 10 digits long).

Fixed
~~~~~
* The Czech bank registry was stored in latin-1 encoding while being read as UTF-8. This resulted
  in invalid bank names `@Natim <https://github.com/Natim>`_ and
  `@Cogax <https://github.com/Cogax>`_.
* The Norwegian national checksum algorithm was rendering wrong results in some edge-cases
  `@Natim <https://github.com/Natim>`_



`2024.01.1`_ - 2024/01/05
-------------------------
Added
~~~~~

* Support aspirational countries:

  * Algeria
  * Angola
  * Benin
  * Burkina Faso
  * Burundi
  * Cabo Verde
  * Cameroon
  * Central African Republic
  * Chad
  * Comoros
  * Congo
  * Côte d'Ivoire
  * Djibouti
  * Equatorial Guinea
  * Gabon,
  * Guinea-Bissau
  * Honduras
  * Iran
  * Madagascar
  * Mali
  * Morocco
  * Mozambique
  * Nicaragua
  * Niger
  * Senegal
  * Togo

* National checksum algorithms for many countries have been added:

  * Albania
  * Bosnia and Herzegovina
  * Czech Republic
  * East Timor
  * Estonia
  * Finland
  * Iceland
  * Mauritania
  * Montenegro
  * North Macedonia
  * Norway
  * Poland
  * Portugal
  * Serbia
  * Slovakia
  * Slovenia
  * Spain
  * Tunisia

* Add new banks to the list of French banks `@Natim <https://github.com/Natim>`_:

  * ARKEA BP Brest
  * Anytime
  * Lydia Bank
  * MEMO BANK
  * Revolut
  * SHINE
  * SumUp Limited

* New :attr:`.IBAN.in_sepa_zone`-property to indicate if the IBAN's country is part of the SEPA
  zone.
* New manual bank registries for

  * Andorra
  * Arabic Emirates
  * Costa Rica
  * Portugal

* New attributes :attr:`.IBAN.account_id`, :attr:`.IBAN.account_holder_id` and
  :attr:`.IBAN.account_type` that are available depending on the country's BBAN specification.
  E.g. :attr:`.IBAN.account_holder_id` is currently only available for Iceland (Kennitala) and only
  Brazil defines an :attr:`.IBAN.account_id`.

Changed
~~~~~~~
* Use enhanced IBAN/BBAN format from `Wikipedia <https://en.wikipedia.org/wiki/International_Bank_Account_Number#IBAN_formats_by_country>`_,
  since the official information from SWIFT is often inacurate.
* The support for national checksum digits has been reimplemented.
* The :class:`.IBAN`-class now has an additional :attr:`.IBAN.bban`-attribute, where all country
  specific functionality has been moved to.
* Updated bank registries. Thanks to `@sh4dowb <https://github.com/sh4dowb>`_ for the Turkish banks.


`2023.11.2`_ - 2023/11/27
-------------------------
Added
~~~~~
* Add OKALI to the list of French banks `@Natim <https://github.com/Natim>`_.

`2023.11.1`_ - 2023/11/27
-------------------------
Changed
~~~~~~~
* The Swiss bank registry is now generated from the SIX Group.
* Manually add missing bank entry for Spain.
* Updated bank registr for Austria and Poland.

`2023.11.0`_ - 2023/11/17
-------------------------
Changed
~~~~~~~
* The validation of a :class:`.BIC` is now performed in the context of ISO 9362:2022 which allows
  numbers in the business party prefix. If strict SWIFT compliance is reqruied the
  ``enforce_swift_compliance`` parameter can be set to ``True``.
* The :meth:`.BIC.from_bank_code`-method will now select the most generic BIC (e.g. with no branch
  specifier or the "XXX" value) if multiple BICs are associated to the given domestic bank code.
  `@Natim <https://github.com/Natim>`_.
* Many manually curated bank registry entries have been re-added by `@dennisxtria <https://github.com/dennisxtria>`_

`2023.10.0`_ - 2023/10/31
-------------------------
Added
~~~~~~~
* The Pydantic v2 protocol is now supported, so that the :class:`.IBAN` and :class:`.BIC` classes
  can be directly used as type annotations in `Pydantic models <https://docs.pydantic.dev/latest/concepts/models/#basic-model-usage>`_

Changed
~~~~~~~
* The :class:`.IBAN` and :class:`.BIC` classes are now subclasses of :class:`str` so that all string
  related methods and functionallities (e.g. slicing) are directly available.

`2023.09.0`_ - 2023/09/25
-------------------------
Removed
~~~~~~~
* Support for Python 3.7 has been dropped.

Added
~~~~~
* New method :meth:`.BIC.candidates_from_bank_code` to list all matching BICs to a given domestic
  bank code `@Natim <https://github.com/Natim>`_.

Changed
~~~~~~~
* The Italian bank registry is now automatically generated thanks to
  `@Krystofee <https://github.com/Krystofee>`_

Internal
~~~~~~~~
* Switch project tooling to `hatch <https://hatch.pypa.io/latest/>`_.
* Use `ruff <https://docs.astral.sh/ruff/>`_ instead of [flake8](https://flake8.pycqa.org/en/latest/)
  as linter.
* Upgrade `mypy <https://www.mypy-lang.org/>`_ to 1.5.1 and fix all new typing errors.

`2023.06.0`_ - 2023/06/21
-------------------------
Fixed
~~~~~
* For Ukrainian banks calling ``iban.bic`` did result in a ``TypeError``. Thanks
  `@bernoreitsma <https://github.com/bernoreitsma>`_ for reporting.

Changed
~~~~~~~
* Updated generated bank registries for Austria, Belgium, Czech Republic, Germany, Netherlands,
  Hungary, Norway, Poland and Ukraine.


`2023.03.0`_ - 2023/03/14
-------------------------
Changed
~~~~~~~
* Updated generated bank registries for Austria, Belgium, Germany, Netherlands,
  Hungary, Slovenia and Ukraine.

Added
~~~~~
* New bank registry for Norway thanks to `@ezet <https://github.com/ezet>`_

`2023.02.1`_ - 2023/02/28
-------------------------
Fixed
~~~~~
* The domestic checksum calculation for Belgium now returns 97 in case the modulo operation
  results in 0. `@mhemeryck <https://github.com/mhemeryck>`_

Changed
~~~~~~~
* Updated generated bank registries for Austria, Belgium, Czech Republic, Germany, Spain,
  Hungary and Croatia.

`2023.02.0`_ - 2023/02/06
-------------------------
Added
~~~~~
* New banks for Portugal and Italy `@dennisxtria <https://github.com/dennisxtria>`_
* Added support for Ukrainian banks `@shpigunov <https://github.com/shpigunov>`_

Fixed
~~~~~
* Corrected bank codes for Cypriot banks `@Krystofee <https://github.com/Krystofee>`_

`2022.09.0`_ - 2022/16/09
-------------------------
Added
~~~~~
* IBAN validation for Senegal `mkopec87 <https://github.com/mkopec87>`_

Changed
~~~~~~~
* Refactored most of the scripts to generate the bank registry to use Pandas `@pebosi <https://github.com/pebosi>`_
* Updated bank registry for Austria, Belgium, Germany, Spain, Hungary, Netherlands and Poland.

`2022.07.1`_ - 2022/28/07
-------------------------
Fixed
~~~~~
* In some countries the BBAN does not include a bank code, but only a branch code (e.g. Poland). In
  those cases the branch code should be used to lookup the bank associated to an IBAN instead of the
  obviously empty bank code.

`2022.07.0`_ - 2022/07/07
-------------------------
Fixed
~~~~~
* Hungarian bank registry generator script was fixed by `@Krystofee <https://github.com/Krystofee>`_

`2022.06.3`_ - 2022/06/29
-------------------------
Added
~~~~~
* Generated list of Lithuanian BICs `@Draugelis <https://github.com/Draugelis>`_
* Removed manually curated list of Lithuanian banks.

`2022.06.2`_ - 2022/06/22
-------------------------
Added
~~~~~
* Generated list of Greek BICs `@kounabi  <https://github.com/kounabi>`_
* Generated list of Cypriot BICs `@kounabi  <https://github.com/kounabi>`_

Changed
~~~~~~~
* Updated bank registry for Austria, Belgium, Czech Republic, Germany, Croatia, Netherlands, Poland
  and Slovenia.

Fixed
~~~~~
* The domestic bank code for Hungarian banks was wrongly generated `@Krystofee <https://github.com/Krystofee>`_

`2022.06.1`_ - 2022/06/06
-------------------------

Added
~~~~~
* Generated list of Romanian BICs `@Krystofee <https://github.com/Krystofee>`_
* Generated list of Hungarian BICs `@Krystofee <https://github.com/Krystofee>`_
* Extended manually curated list of Irish BICs `@dennisxtria <https://github.com/dennisxtria>`_


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


.. _2026.11.0: https://github.com/mdomke/schwifty/compare/2026.10.1...2026.11.0
.. _2026.10.1: https://github.com/mdomke/schwifty/compare/2026.10.0...2026.10.1
.. _2026.10.0: https://github.com/mdomke/schwifty/compare/2026.07.3...2026.10.0
.. _2026.07.3: https://github.com/mdomke/schwifty/compare/2026.07.2...2026.07.3
.. _2026.07.2: https://github.com/mdomke/schwifty/compare/2026.07.1...2026.07.2
.. _2026.07.1: https://github.com/mdomke/schwifty/compare/2026.07.0...2026.07.1
.. _2026.07.0: https://github.com/mdomke/schwifty/compare/2026.03.0...2026.07.0
.. _2026.03.0: https://github.com/mdomke/schwifty/compare/2026.01.0...2026.03.0
.. _2026.01.0: https://github.com/mdomke/schwifty/compare/2025.09.0...2026.01.0
.. _2025.09.0: https://github.com/mdomke/schwifty/compare/2025.07.0...2025.09.0
.. _2025.07.0: https://github.com/mdomke/schwifty/compare/2025.06.0...2025.07.0
.. _2025.06.0: https://github.com/mdomke/schwifty/compare/2025.01.0...2025.06.0
.. _2025.01.0: https://github.com/mdomke/schwifty/compare/2024.11.0...2025.01.0
.. _2024.11.0: https://github.com/mdomke/schwifty/compare/2024.09.0...2024.11.0
.. _2024.09.0: https://github.com/mdomke/schwifty/compare/2024.08.1...2024.09.0
.. _2024.08.1: https://github.com/mdomke/schwifty/compare/2024.08.0...2024.08.1
.. _2024.08.0: https://github.com/mdomke/schwifty/compare/2024.06.1...2024.08.0
.. _2024.06.1: https://github.com/mdomke/schwifty/compare/2024.06.0...2024.06.1
.. _2024.06.0: https://github.com/mdomke/schwifty/compare/2024.05.4...2024.06.0
.. _2024.05.4: https://github.com/mdomke/schwifty/compare/2024.05.3...2024.05.4
.. _2024.05.3: https://github.com/mdomke/schwifty/compare/2024.05.2...2024.05.3
.. _2024.05.2: https://github.com/mdomke/schwifty/compare/2024.05.1...2024.05.2
.. _2024.05.1: https://github.com/mdomke/schwifty/compare/2024.05.0...2024.05.1
.. _2024.05.0: https://github.com/mdomke/schwifty/compare/2024.04.0...2024.05.0
.. _2024.04.0: https://github.com/mdomke/schwifty/compare/2024.01.1...2024.04.0
.. _2024.01.1: https://github.com/mdomke/schwifty/compare/2023.11.2...2024.01.1
.. _2023.11.2: https://github.com/mdomke/schwifty/compare/2023.11.1...2023.11.2
.. _2023.11.1: https://github.com/mdomke/schwifty/compare/2023.11.0...2023.11.1
.. _2023.11.0: https://github.com/mdomke/schwifty/compare/2023.10.0...2023.11.0
.. _2023.10.0: https://github.com/mdomke/schwifty/compare/2023.09.0...2023.10.0
.. _2023.09.0: https://github.com/mdomke/schwifty/compare/2023.06.0...2023.09.0
.. _2023.06.0: https://github.com/mdomke/schwifty/compare/2023.03.0...2023.06.0
.. _2023.03.0: https://github.com/mdomke/schwifty/compare/2023.02.1...2023.03.0
.. _2023.02.1: https://github.com/mdomke/schwifty/compare/2023.02.0...2023.02.1
.. _2023.02.0: https://github.com/mdomke/schwifty/compare/2022.09.0...2023.02.0
.. _2022.09.0: https://github.com/mdomke/schwifty/compare/2022.07.1...2022.09.0
.. _2022.07.1: https://github.com/mdomke/schwifty/compare/2022.07.0...2022.07.1
.. _2022.07.0: https://github.com/mdomke/schwifty/compare/2022.06.3...2022.07.0
.. _2022.06.3: https://github.com/mdomke/schwifty/compare/2022.06.2...2022.06.3
.. _2022.06.2: https://github.com/mdomke/schwifty/compare/2022.06.1...2022.06.2
.. _2022.06.1: https://github.com/mdomke/schwifty/compare/2022.06.0...2022.06.1
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
