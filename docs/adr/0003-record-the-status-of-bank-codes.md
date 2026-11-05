# 3. Record the status of bank codes separately from `primary`

Date: 2026-11-03

## Status

Accepted. Refines [ADR 2](0002-keep-retired-bank-codes-and-hide-closed-banks.md).

## Relation to ADR 2

Status: Supersedes the hiding of closed banks decided in ADR 2.

ADR 2 keeps retired bank codes, marks them with a `retired` flag, takes name and BIC of merged
codes from their successor while keeping their own BIC as `legacy_bic`, and leaves closed banks
(retired without a successor) out of the lookups unless `include_closed=True` is given. This ADR
was written in parallel and replaces the `retired` flag with a status, which also tells apart why
a code was retired. The two are combined as follows:

- `status` is the only field that records the fate of a bank code. `Bank` has no derived flags
  such as `retired`, `closed` or `active`, since they only restate the status.
- Lookups return closed and delisted banks as well, ranked below active and merged records of the
  same code (see *Lookups* below), and `include_closed` is dropped. `IBAN.bank` exists to
  identify the bank of an IBAN, and the status tells whether payments can be made to it. Leaving
  closed banks out would withhold exactly that information, and would make `IBAN.bank` return
  `None` for a bank code that the registry knows.
- Merged codes keep both their `legacy_name` (this ADR) and their `legacy_bic` (ADR 2).
- Everything else of ADR 2 stands, e.g. that a merged code keeps the checksum method of the
  original bank and that `IBAN.random()` never picks a retired code.

## Context

A national bank code can map to several [bank records](../../CONTEXT.md#bank-record), e.g.
one per branch or one per BIC. `Bank.primary` marks the record that represents the bank code
itself. It is only used to break ties: `IBAN.bank` (and with it `bank_name` and
`bank_short_name`) as well as `BIC.from_bank_code` and `BIC.candidates_from_bank_code` prefer
primary records. Every registry source that sets the flag means exactly that, e.g. the
Bundesbank's "Merkmal", the head office (`HEADQUARTERS`, `TYP == 0`, `Institutsart` KI) of the
Swiss, Ukrainian and Austrian sources, or the preferred BIC of a bank code in the UK and Sweden.

Registries used to drop bank codes as soon as they disappeared from the official source, although
IBANs carrying them stay in circulation. To keep them resolvable, the update scripts now keep such
codes from the previous registry (`scripts/retired.py`). All of these records are stored as
`primary: false`, so that lookups prefer the banks that are still listed.

Overloading `primary` this way has three problems:

- **The status is not exposed.** `IBAN(...).bank` returns a closed bank exactly like an active
  one. Callers cannot tell that an IBAN belongs to a bank that no longer exists.
- **The meanings blur.** `primary: false` can now mean "branch", "no longer listed", or both. A
  retired head office, e.g. Austria's `20315`, is indistinguishable from a branch.
- **Information is lost.** The source's own primary flag of a retired record is overwritten, and
  what some sources state about the fate of a bank is reduced to a tie-breaker.

A single "inactive" flag would not be enough either, because a bank code that is no longer listed
can mean opposite things for a user:

- **Merged:** the bank was taken over, and payments to its IBANs reach the successor. Some sources
  state the successor's code (merged IIDs in Switzerland, the aliases of Slovenia, Spain's
  "BAJA POR FUSION ... POR 2100", the Bundesbank's successor bank codes), others only its name
  (run-off codes in the Czech Republic and Slovakia).
- **Closed:** the bank no longer exists and has no successor (Spain's "BAJA POR CIERRE",
  Ukraine's banks in liquidation).
- **Unknown:** most sources only list current codes, so all that is known is that a code is no
  longer listed (e.g. Austria, Belgium, Finland, the Netherlands, Norway, the UK).

## Decision

Add a status and two optional fields to the `Bank` domain object, and restrict `primary` to its
original meaning.

- **`primary`** marks the record that represents a bank code among several records for that code
  (head office versus branch, preferred versus secondary BIC). It is taken from the source and no
  longer changed when a bank code is retired.
- **`status`** is a `BankStatus` (`enum.StrEnum`) describing the bank code:
  - `active`: listed by the official source. This is the default.
  - `merged`: the bank was taken over or the code was replaced, so the code still leads to an
    institution, the successor.
  - `closed`: the bank was closed and has no successor.
  - `delisted`: the code is no longer listed by the source, and the source doesn't say why.
- **`successor_bank_code`** is the bank code of the successor of a `merged` record, where the
  source states it.
- **`legacy_name`** is the name a `merged` code was last listed under, where `name` describes the
  successor. `name`, `short_name` and `bic` always describe the institution that services the
  bank code today: the successor for `merged` records where it is known, and the bank itself
  otherwise. For example, the Slovenian code `06000` of the former Abanka has the name and BIC of
  OTP banka, and `legacy_name` "NOVA KBM D.D.", the name it was last listed under.

  A successor's bank code alone is not enough to rename a record: the source also has to know
  which institution services the code today. iban.es, the source of the Spanish registry, states
  the successor of every merged bank, but still lists some successors as active that have merged
  themselves since, e.g. Bankia (merged into CaixaBank in 2021) or Banco Popular (merged into
  Banco Santander in 2018). Following the chain of successors would therefore replace a bank's
  name with an outdated one. Merged Spanish codes keep their own name and BIC instead, and carry
  only the `successor_bank_code`.

  The Spanish update script corrects iban.es where it is known to lag behind, each correction
  with its source (e.g. Bankia merged into CaixaBank). A correction confirms which bank services
  its code today, so a chain of successors whose last step is a correction is followed after all,
  and the code gets the name and BIC of that bank, e.g. Caja Madrid -> Bankia (iban.es) ->
  CaixaBank (correction).
- **Lookups** rank the records of a bank code first by status and then by `primary`:
  1. `active` records,
  2. `merged` records, since they lead to a successor that still services the code,
  3. `closed` and `delisted` records, which rank equally.

  Within each group, primary records come before non-primary ones, so among the active records
  the head office is still preferred over its branches. Records of retired bank codes still
  resolve, so existing IBANs keep their bank name and BIC.
- **Registry files** only contain the new keys where they differ from the default. A missing
  `status` means `active`, so existing and manual registries stay valid without changes, and
  diffs stay small.
- **`convert_to_v2`** groups records by the new fields as well as by `primary`, so they survive the
  conversion.
- **`CONTEXT.md`** defines `primary`, the status values, `successor_bank_code` and `legacy_name`.

### Implementation in two steps

1. **Model and migration.** The new fields, the lookup order, `convert_to_v2`, and the update
   scripts that already tell the cases apart:
   - `scripts/retired.py` marks the records it keeps as `delisted`.
   - The aliases of Switzerland and Slovenia become `merged`, with successor and legacy name.
   - The run-off codes of the Czech Republic and Slovakia become `merged`, without a successor
     code, and keep the bank's own name.
   - Ukraine's banks in liquidation become `closed`.

   Today's retired records all carry `primary: false`, and their original flag is not stored
   anywhere. Rerunning the update scripts sets their status, and their original `primary` value is
   restored from git history, from the last registry version in which the bank code was still
   listed. Manual registries in which records were marked non-primary because the bank closed or
   merged (Bosnia, Serbia, Moldova) are corrected by hand.
2. **Reasons from the sources.** Per country, where the source states why a code was retired:
   Spain's "BAJA" texts (merger with successor code versus closure), the Bundesbank's successor
   bank codes, and Italy's cessation reasons, if its registers provide them.

## Alternatives considered

- **Keep overloading `primary`.** Lookups already behave as intended, but the status stays
  invisible to callers and the field keeps two meanings.
- **A single `active` flag.** It would mark merged banks, whose IBANs still reach the successor,
  as inactive like closed ones, which is misleading. It also cannot express that the fate of most
  retired codes is unknown.
- **Keeping the original bank's name in `name` for merged codes**, and referring to the successor
  only through `successor_bank_code`. This describes the code's history more directly, but changes
  what `bank_name` and `bic` return for IBANs that resolve to the successor today. `legacy_name`
  keeps that behaviour and still preserves the original name.
- **A retirement date or free-text reason**, e.g. `valid_until` or Spain's "BAJA POR FUSION ...".
  Few sources provide them, so they are left out. They can be added later as optional fields.
- **Separate registry files for retired banks**, e.g. `retired_at.json`. This keeps the active
  registries clean, but the registry has to merge the files again for lookups, and the update
  scripts would have to move records between files.

## Consequences

- **New public API.** `Bank.status`, `Bank.successor_bank_code`, `Bank.legacy_name` and
  `BankStatus` need a changelog entry. All have defaults, so code that constructs `Bank` objects
  keeps working.
- **Lookup results stay the same** for active banks and for aliases. For bank codes with several
  records, a retired head office now ranks below an active branch, which is the intended
  behaviour.
- **One-off migration** of the generated registries, which touches many files once.
- **`primary` regains a single meaning**, which future update scripts and reviews should keep: the
  status of a bank code belongs into `status`, not into `primary`.
