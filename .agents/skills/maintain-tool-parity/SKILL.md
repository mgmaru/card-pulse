---
name: maintain-tool-parity
description: Add, change, or remove a Codex/Claude Code research subagent, or a shared skill, so both tools stay in parity. Use when editing agent definitions, adding a skill, or investigating why one tool sees configuration the other does not; do not use for ordinary code or documentation changes.
---

# Maintain Tool Parity

This repository is developed with both OpenAI Codex and Claude Code. The two tools read
different paths, so a change made for one tool is invisible to the other unless it is
made in the shared location and generated outward.

## Where configuration lives

| Concern | Shared source of truth | Generated or linked for each tool |
| --- | --- | --- |
| Research subagents | `.agents/agents/<slug>.md` | `.codex/agents/<slug>.toml`, `.claude/agents/<slug>.md` |
| Skills | `.agents/skills/<name>/` | `.claude/skills/<name>` symlink |
| Repository instructions | `AGENTS.md` | `CLAUDE.md` imports it with `@AGENTS.md` |

Codex reads `.agents/skills/` directly; Claude Code reads only `.claude/skills/`. Neither
tool reads the other's agent directory, so agent files are generated for both.

## Workflow

1. Edit the shared source of truth. Never edit a generated file directly:
   - a subagent's behavior belongs in `.agents/agents/<slug>.md`
   - a skill's behavior belongs in `.agents/skills/<name>/SKILL.md`
2. Regenerate the per-tool files and repair skill symlinks:

   ```bash
   python3 .agents/skills/maintain-tool-parity/scripts/check_tool_parity.py --write
   ```

3. Verify, and report the result:

   ```bash
   python3 .agents/skills/maintain-tool-parity/scripts/check_tool_parity.py
   ```

4. Commit the shared source **and** every generated file together. CI re-runs the check on
   a clean checkout, so a generated file left uncommitted fails the build.

## Agent definition format

Frontmatter keys are tool-neutral and map to each tool's own vocabulary:

| Key | Codex | Claude Code |
| --- | --- | --- |
| `access: read-only` \| `workspace-write` | `sandbox_mode` | omits or includes `Edit`, `Write` |
| `web: true` \| `false` | — | includes `WebSearch`, `WebFetch` |
| `delegation: none` \| `allowed` | instruction text only | omits or includes `Agent` |
| `reasoning-effort` | `model_reasoning_effort` | `effort` |
| `codex-model` / `claude-model` | `model` | `model` |

Write the instruction body once, in the shared file. It is embedded verbatim in both
generated files, so both tools receive identical instructions.

## Boundaries

- The check is structural. It verifies that both tools receive the same instruction body
  and can see the same skills. It does not judge whether the instructions are good.
- Codex and Claude Code model names are not equivalent. Choosing `codex-model` and
  `claude-model` is a human decision the script does not validate.
- `.codex/config.toml` and `.claude/settings.json` are not compared. Their options do not
  map one-to-one, so keep them aligned by hand.
- A description containing `"`, or a body containing `"""`, cannot be represented in the
  Codex TOML format. The script fails rather than emitting a broken file.
