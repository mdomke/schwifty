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
