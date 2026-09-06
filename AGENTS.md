# Repository instructions

## Project context

- Card Pulse is an independent TCG market-data foundation. It collects, preserves, normalizes, and queries price observations.
- Read `README.md`, `docs/product/mvp.md`, and relevant ADRs before changing behavior or architecture.
- Treat `docs/research/` as historical or time-bound research, not as the current specification.

## Language and naming

- Write project documentation and user-facing explanations in Japanese.
- Use English identifiers for Python modules, types, functions, database objects, and schemas.
- Use source slugs that remain stable even if a shop's display name changes.

## Architecture

- Keep domain rules independent from HTTP, HTML parsers, a specific database product, OCR, and command-line concerns.
- Put source-specific acquisition and parsing under `src/card_pulse/adapters/sources/<source-slug>/`.
- Preserve raw artifacts before parsing. Parsing must be repeatable from stored artifacts or approved fixtures.
- Keep stored observations append-only. Express corrections and reparsing as new history rather than overwriting evidence.
- Route ambiguous card identities to review instead of confirming a name-only match.
- Keep API, collection worker, and database as separate runtime services while sharing domain and application code in this repository.
- Use Docker Compose to reproduce the local service topology. Do not treat it as a complete reproduction of managed production infrastructure.

## Data and tests

- Never commit credentials, cookies, personal information, fetched raw artifacts, local databases, or runtime logs.
- Do not access live external sources from automated tests.
- Use only sanitized fixtures whose storage and reuse are permitted.
- Test idempotency, provenance, missing fields, malformed prices, parser regressions, and failure isolation when those areas change.

## Documentation

- Update relevant product, architecture, contract, source, or runbook documents with behavioral changes.
- Record decisions that affect several components or constrain future work in an ADR.
- Add a checked date and supporting URL to source restrictions, prices, rate limits, terms, and other volatile external facts.
- Prefer migrations, code types, and machine-readable schemas as field-level sources of truth. Document their meaning and invariants instead of duplicating them.
