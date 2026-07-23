# AGENTS.md

Orientation for AI coding agents working on `schwifty`. This file is an index and a
short list of conventions — the authoritative docs live elsewhere and are linked below.

## Where to look

- **Setup & commands** → [`CONTRIBUTING.rst`](CONTRIBUTING.rst). How to install (`uv`), the
  full list of `poe` tasks, and how to test against a specific Python version.
- **Domain vocabulary** → [`CONTEXT.md`](CONTEXT.md). What IBAN, BIC, BBAN, checksum
  method, registry and IBAN spec mean in this codebase. Read this before touching
  validation or registry code.
- **Design decisions** → [`docs/adr/`](docs/adr/). Why the code is shaped the way it is
  (e.g. typed domain objects with deprecated dict access).
- **Changelog** → [`CHANGELOG.rst`](CHANGELOG.rst).

## Everyday loop

Project tasks run through `poe` via `uv`. The two you need most:

```bash
uv run poe check   # lint, format check, type check, doc lint
uv run poe test    # test suite + doctests with coverage
```

Run `uv run poe` with no arguments to list every task. Optional dependencies (e.g.
`pydantic`) are provided to tasks with `uv run --extra <name>`, **not** by adding them to
the dev dependency group — this is how `test` and `check-types` already pull in `pydantic`.

## Conventions

- **Keep `schwifty/` strict.** Ruff relaxations are scoped by directory in
  `[tool.ruff.lint.per-file-ignores]` — `scripts/`, `tests/` and docs get exceptions; the
  library package does not. Don't widen ignores to cover `schwifty/`; fix the code instead.
- **Python support.** Code must run on CPython 3.10 through 3.14. Avoid features newer than
  3.10 (for example, `StrEnum` — see the commit history).
- **Update the changelog.** Add an entry to `CHANGELOG.rst` describing user-visible changes.

## Before you're done

- `uv run poe check` and `uv run poe test` both pass.
- A `CHANGELOG.rst` entry exists for the change.
- Work on a topic branch and open a pull request against `main` (see `CONTRIBUTING.rst`).
