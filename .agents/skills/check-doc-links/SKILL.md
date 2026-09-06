---
name: check-doc-links
description: Check repository-internal Markdown file links, image links, and heading anchors after documentation is created, edited, moved, renamed, or deleted. Use for explicit link-check requests and documentation changes; do not use for code-only changes that cannot affect Markdown links.
---

# Check Doc Links

Validate documentation links deterministically before considering a Markdown change complete.

## Workflow

1. Resolve the repository root and identify all Markdown files affected by the task, including moved and deleted targets.
2. Run the full internal-link check from the repository root:

   ```bash
   python3 .agents/skills/check-doc-links/scripts/check_doc_links.py
   ```

3. Fix broken relative paths, missing files, non-portable absolute paths, and missing Markdown heading anchors introduced by the change.
4. Run the check again. Report the checked file/link counts and any unresolved pre-existing failures.

Use `--root <path>` only when checking another repository or an isolated fixture. Pass specific files or directories after the options only for diagnosis; use the full scan for final validation.

## Boundaries

- The script checks repository-local Markdown and image targets without network access.
- It deliberately skips `http`, `https`, `mailto`, and other remote schemes. Check external URLs only when the user explicitly asks, because availability, redirects, rate limits, and bot protection make that check non-deterministic.
- Do not invent a target when a broken link has more than one plausible destination. Report the ambiguity.
- Preserve the intended section when repairing an anchor; do not merely remove the fragment to make the check pass.
- Run relevant document-specific validation in addition to this script. For example, roadmap changes also require the roadmap validator.
