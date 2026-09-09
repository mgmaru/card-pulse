# Repository instructions

Card Pulse is developed with both OpenAI Codex and Claude Code. `AGENTS.md` is the
single source of truth for repository instructions and applies to both tools. Do not
copy its content into this file.

@AGENTS.md

## Claude Code specifics

- `AGENTS.md` names research subagents with their Codex identifiers. The Claude Code
  equivalents are `source-feasibility-researcher` and `source-restrictions-researcher`.
- Skills live in `.agents/skills/`. `.claude/skills/` contains only symlinks to them.
  Edit skills at their real path under `.agents/skills/`, never through `.claude/skills/`.
- `.claude/agents/*.md` are generated files. Edit `.agents/agents/<slug>.md` instead, then
  run the `maintain-tool-parity` skill so Codex and Claude Code receive the same change.
