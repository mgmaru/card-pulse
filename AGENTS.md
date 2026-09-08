# Repository instructions

## Project context

- Card Pulse is an independent TCG market-data foundation. It collects, preserves, normalizes, and queries price observations.
- Read `README.md`, `docs/product/mvp.md`, and relevant ADRs before changing behavior or architecture.

## Context selection

- Use filenames and targeted searches to select context. Read only files and sections directly relevant to the current task, and do not preload entire documentation directories.
- Do not search, enumerate, or read `_prompts/`. When the user explicitly supplies an excerpt from `_prompts/`, treat that excerpt as the request without opening the surrounding file. Inspect a prompt file only when the user explicitly asks for that file itself.
- Do not read `docs/learning/` or `docs/research/` by default. Read a specific file only when the task explicitly concerns that material or a current source-of-truth document identifies it as required input.
- Treat `docs/research/` as historical or time-bound evidence, not as the current specification.
- Read `docs/experiments/`, `docs/runbooks/`, `docs/sources/`, and files named `template.md` only when the current task concerns that document type or component.
- Do not recursively inspect `var/`. Access only an explicitly identified artifact when the current task requires it.
- Deterministic validation scripts and CI may scan paths excluded from normal context selection. Do not load the scanned file contents into model context unless one of the conditions above applies.

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

## Parallel research

- Use subagents when two or more independent research tracks can run concurrently and parallel execution is likely to save time or improve evidence coverage.
- During Phase 0, assign one named source to each `source_feasibility_researcher`, then use `source_restrictions_researcher` to verify restrictions for shortlisted sources.
- Keep research subagents read-only. They return evidence and unresolved questions; the primary agent reconciles conflicts and makes repository edits.
- Only the primary agent delegates Phase 0 research. Research subagents must not create additional subagents.
- Wait for all requested research results before making a recommendation, and distinguish confirmed facts, inferences, conflicts, and unknowns in the synthesis.
- Keep short or tightly dependent work in the primary agent when delegation would add more coordination than useful independent investigation.

## Documentation

- Update relevant product, architecture, contract, source, or runbook documents with behavioral changes.
- Record decisions that affect several components or constrain future work in an ADR.
- Add a checked date and supporting URL to source restrictions, prices, rate limits, terms, and other volatile external facts.
- Prefer migrations, code types, and machine-readable schemas as field-level sources of truth. Document their meaning and invariants instead of duplicating them.
- Run `python3 .agents/skills/check-doc-links/scripts/check_doc_links.py` after creating, editing, moving, renaming, or deleting Markdown documentation.
- Use the repository roadmap task format and run `python3 .agents/skills/maintain-roadmap/scripts/validate_roadmap.py` after roadmap changes.
