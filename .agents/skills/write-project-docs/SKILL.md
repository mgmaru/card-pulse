---
name: write-project-docs
description: Create or substantially revise Card Pulse Markdown documentation using the repository's source-of-truth hierarchy, document types, templates, and appropriate prose, tables, lists, and Mermaid diagrams. Use for project documentation work other than roadmap task-state management; do not trigger for typo-only edits or code-only changes.
---

# Write Project Docs

Create documentation that answers a defined reader question and remains maintainable with the codebase.

## Start with authority and document type

1. Read `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, and the documents directly related to the requested change.
2. Identify the intended reader, the decision or behavior being documented, and the canonical source of truth.
3. Choose the destination by purpose:

   | Purpose | Location |
   | --- | --- |
   | Product purpose, scope, roadmap | `docs/product/` |
   | Domain terminology | `docs/domain/` |
   | Current system design and data model | `docs/architecture/` |
   | Component and external boundaries | `docs/contracts/` |
   | Adopted decisions and their rationale | `docs/adr/` |
   | Source-specific facts and restrictions | `docs/sources/` |
   | Time-bound investigation | `docs/research/` |
   | Repeatable operational procedure | `docs/runbooks/` |
   | Experiment evidence and outcome | `docs/experiments/` |
   | Explanatory study material | `docs/learning/` |

Use the `maintain-roadmap` workflow for task IDs, state changes, interruption, and resumption. When a request changes both documentation and roadmap tasks, apply both sets of rules.

## Write for the document's job

- Lead with the outcome, decision, or purpose, then provide the reasoning and evidence needed to assess it.
- Use connected prose for background, reasoning, tradeoffs, and implications.
- Use bullet lists for genuinely parallel conditions or steps.
- Use tables for mappings or comparisons with repeated fields.
- Use Mermaid when relationships, sequence, state, ownership, or data flow are materially clearer as a visual. Choose `flowchart`, `sequenceDiagram`, `stateDiagram-v2`, or `erDiagram` to match the relationship.
- Do not add a diagram, table, or list solely to satisfy a format rule.
- Keep examples concrete and consistent with current names such as API, Collection Worker, DB, artifact storage, and Card Digger.

## Preserve sources of truth

- Treat `docs/product/`, `docs/architecture/`, `docs/contracts/`, and accepted ADRs as current guidance. Treat `docs/research/` as historical or time-bound evidence.
- Record a multi-component or future-constraining decision in a new ADR. Do not rewrite a superseded ADR's historical decision.
- Add a checked date and supporting URL to volatile external facts such as terms, prices, rate limits, versions, and access restrictions.
- Keep field-level definitions in migrations, code types, or machine-readable schemas once they exist. Explain meaning and invariants in Markdown rather than duplicating generated detail.
- Link to an existing explanation instead of copying it into multiple documents.
- Update affected indexes and incoming links when moving, renaming, or replacing a document.

Use existing repository templates when applicable:

- `docs/adr/template.md`
- `docs/sources/template.md`
- `docs/experiments/README.md`
- `docs/runbooks/README.md`

## Validate

After changing Markdown:

1. Check that status, dates, links, and referenced decisions remain consistent.
2. Run:

   ```bash
   python3 .agents/skills/check-doc-links/scripts/check_doc_links.py
   ```

3. Run any document-specific validator, including the roadmap validator when the roadmap changed.
4. Summarize what changed, why, and which validation passed.
