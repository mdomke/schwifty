# 2. Keep retired bank codes, but hide closed banks by default

Date: 2026-10-30

## Status

Accepted

## Context

National registries drop bank codes once a bank merges or closes, but IBANs carrying those
codes stay in circulation for years. Regenerating a registry used to drop them as well, so
`IBAN.bank` and `IBAN.bic` silently returned `None` for such IBANs, and for Germany the
per-bank checksum method was lost with them, so their account codes weren't checked anymore.

The Swiss and Slovenian registries already kept the codes of merged banks as aliases of the
successor, and the Latvian and German update scripts started to keep retired codes as well.
None of these entries were marked, though: a library user could not tell an active bank from
one that no longer exists, and might initiate a payment to a bank that was closed.

Retired bank codes fall into two groups:

- **Merged:** the code has an active successor. Resolving it to the successor is what users
  need, also for payments.
- **Closed:** there is no successor. The bank is useful to identify an old IBAN, but must not
  be used for anything that moves money.

We considered dropping closed banks entirely, keeping them in separate registry files, and
excluding every retired code from the lookups, including merged ones. The latter would have
changed results for the Swiss and Slovenian aliases that previous releases already resolved.

## Decision

- Registry entries of retired bank codes carry `"retired": true`. Merged ones also carry
  `"successor_bank_code"` and take name and BIC from the successor. `Bank` exposes both as
  `retired` and `successor_bank_code`, and `Bank.closed` is true for retired codes without a
  successor. A merged bank's own BIC is kept as `legacy_bic`, so that BIC lookups still find
  the retired bank code, and `BIC.exists` is true for it: the BIC identifies a known bank, and
  `Bank.bic` gives the one to use for payments.
- Lookups return merged codes as before, but leave closed banks out unless asked for with
  `include_closed=True`: `IBAN.get_bank()`/`BBAN.get_bank()`, `BIC.from_bank_code()`,
  `BIC.candidates_from_bank_code()` and the `registry.get_banks_by_*()` functions. The
  properties `IBAN.bank`, `IBAN.bic`, `BIC.exists` and friends use the default.
- National checksums are always validated with the bank's own method, including closed
  banks, and a merged code keeps the method of the original bank, since the account codes
  were issued by it.
- `IBAN.random()` never picks a retired bank code.
- IBAN validation is unchanged: an IBAN with a retired bank code is still a well-formed IBAN.
- No date of retirement is recorded. The update scripts only know when they first missed a
  code, which is not when the bank stopped operating.
- German closed banks are only kept if their checksum method is known. Older registry
  versions didn't record it, and an entry without it adds little over not knowing the bank.

## Consequences

- Payment flows that rely on `IBAN.bank` or `IBAN.bic` can't end up at a closed bank.
- Users who need to identify old IBANs can still do so explicitly.
- Update scripts that keep retired codes have to mark them, and the v2 file format has to
  keep retired and active entries in separate groups (see `scripts/remap.py`).
- The registry for a country grows over time, as retired codes are never removed
  automatically.
