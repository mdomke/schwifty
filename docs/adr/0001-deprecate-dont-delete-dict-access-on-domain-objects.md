# 1. Deprecate, don't delete, dict-style access on domain objects

Date: 2026-07-22

## Status

Accepted

## Context

Before the registry was refactored to return strongly typed domain objects
(`2026.07.2`), the public properties `IBAN.spec` / `IBAN.bank` (and the `BBAN`
counterparts) returned plain `dict`s. Callers in the wild therefore rely on
subscription and `.get()`, e.g. `iban.bank["name"]` and
`iban.spec["bban_length"]`.

The typed refactor introduced `IBANSpec` and `Bank` dataclasses and, to avoid
breaking those callers, added a `DictCompatMixin` that forwards `__getitem__`
and `get()` to attribute access.

An architecture review flagged the mixin as a shallow, dual-shape seam and
proposed deleting it so there is a single canonical shape. A naive deletion,
however, is a **public breaking change**:

- `IBAN.bank` / `IBAN.spec` returning dicts is a contract from already-shipped
  releases, not just an internal convenience.
- The project uses CalVer (`YY.0M.Micro`), which has no major-version signal to
  telegraph a hard break.
- The project's established convention for retiring public surface is a
  `DeprecationWarning` kept in place for a long time (see the deprecated plural
  properties on `BIC`, warned since 2020 and still present).

The bug that motivated the review — the German per-bank checksum being silently
skipped — was caused by the typed `Bank` dropping the `checksum_algo` field, and
is fixed independently of the mixin by adding that field. So the mixin question
is purely about the public dict-access surface.

## Decision

Keep `DictCompatMixin` on `Bank` and `IBANSpec`, but have `__getitem__` and
`get()` emit a `DeprecationWarning` pointing users to attribute access.
Attribute access (`bank.name`, `spec.bban_length`) is the canonical, blessed
shape; dict access is a documented, warned adapter on its way out.

All internal callers and tests use attribute access only, so the deprecation
warning fires exclusively for external dict-style users.

## Consequences

- **No hard break now.** Existing `iban.bank["name"]` code keeps working, but
  surfaces a `DeprecationWarning` guiding migration.
- **Directional deepening.** The dual-shape ambiguity becomes a one-way,
  removable adapter rather than an open-ended contract.
- **Future removal is a separate, deliberate decision.** Once a suitable
  deprecation window has passed, the mixin can be removed in its own change.
- **Do not re-propose a naive deletion.** A future architecture review that
  spots the mixin as a shallow seam should treat this ADR as the reason it is
  retained; deletion requires ending the deprecation window first, not
  re-litigating the trade-off.
