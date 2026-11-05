# Domain Glossary: schwifty

This document establishes the ubiquitous language and domain vocabulary for the `schwifty` library.

## Core Domain Concepts

### IBAN (International Bank Account Number)
An internationally agreed system of identifying bank accounts across national borders with a
minimal of risk of propagating errors. Consists of a country code, two check digits, and a BBAN.

### BIC (Business Identifier Code)
An 8- or 11-character code defined by ISO 9362 to uniquely identify financial institutions and
non-financial business entities.

### BBAN (Basic Bank Account Number)
The national bank account number format specific to each central bank or payment authority.
It forms the core of an IBAN (excluding the country code and IBAN check digits).

### Checksum
National or international algorithms (e.g., ISO 7064, Modulo-97, Luhn) used to verify the structural
and mathematical correctness of IBANs and BBANs.

### Checksum Method (`checksum_algo`)
The identifier selecting *which* national checksum algorithm applies to a specific bank. Most
countries use a single algorithm keyed as `<country>:default`, but Germany defines dozens of
per-bank methods (e.g. `DE:13`). A `Bank` carries its `checksum_algo` so that
`BBAN.validate_national_checksum` can pick the right algorithm; a bank without an explicit method
falls back to `default`.

Not every country that declares a national check digit in its BBAN specification has such an
algorithm registered. Where none exists, `BBAN.validate_national_checksum` accepts the digits as
they are and emits a `NationalChecksumNotVerified` warning, so the skip is neither silent nor an
error.

## Structural & System Concepts

### Registry
The deep, domain-specific subsystem that handles lazy loading, data merging, on-demand indexing,
and structured queries for banks, country specification maps, and BICs.

### IBAN Spec
The domain representation of a country's IBAN structure and requirements, encapsulating positional
ranges of sub-components and compiled validation regular expressions.

### Bank Record
The metadata representation of a specific bank branch, mapping national components
(e.g., country code, bank code, branch code) to its name, short name, associated BIC, and
[Checksum Method](#checksum-method-checksum_algo). Modelled as the strongly typed `Bank` domain
object; dict-style access to it is deprecated in favour of attribute access.

A bank code can map to several bank records, e.g. one per branch or one per BIC. Lookups by bank
code (`IBAN.bank`, `IBAN.bic`, `BIC.from_bank_code`) all pick the same one of them: by their
[status](#bank-status-status) first, then by how generic their BIC is, then by `primary` (see
[ADR 3](docs/adr/0003-record-the-status-of-bank-codes.md)). A bank code can belong to several
institutions, e.g. Revolut Ltd and Revolut Bank UK share the UK bank code `REVO`;
`BIC.candidates_from_bank_code` lists all of them.

### Primary Record (`primary`)
The bank record that represents a bank code among several records for that code: the head
office as opposed to its branches, or the preferred BIC as opposed to secondary ones. It is
taken from the official source and says nothing about whether the bank still exists.

### Retired Bank Code
A bank code that the national registry no longer lists, but that schwifty keeps because IBANs
carrying it are still in circulation. Its [status](#bank-status-status) tells what became of it.
Lookups return retired codes like active ones, but rank them below active records of the same
code. See [ADR 2](docs/adr/0002-keep-retired-bank-codes-and-hide-closed-banks.md) and
[ADR 3](docs/adr/0003-record-the-status-of-bank-codes.md).

### Bank Status (`status`)
The `BankStatus` of a bank code: `active` while the official source lists it, otherwise one of
the following.

- `merged`: the bank was taken over or the code was replaced, so the code still leads to a
  successor. `successor_bank_code` names the successor's bank code where the source states it.
  `name`, `short_name` and `bic` then describe the bank that services the code today, while
  `legacy_name` and `legacy_bic` hold the name and BIC the code was last listed with, so that its
  BIC still resolves. The checksum method stays the one of the original bank.
- `closed`: the bank was closed and has no successor.
- `delisted`: the code is no longer listed, and the source doesn't say why.
