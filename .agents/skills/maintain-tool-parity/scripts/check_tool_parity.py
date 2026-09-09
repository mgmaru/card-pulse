#!/usr/bin/env python3
"""Keep Codex and Claude Code agent configuration in parity.

Agent definitions live once under `.agents/agents/`. This script renders them into
each tool's native format and verifies that the committed files match, that every
shared skill is visible to both tools, and that Claude Code still imports AGENTS.md.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

NEUTRAL_AGENTS = Path(".agents/agents")
SHARED_SKILLS = Path(".agents/skills")
CODEX_AGENTS = Path(".codex/agents")
CLAUDE_AGENTS = Path(".claude/agents")
CLAUDE_SKILLS = Path(".claude/skills")
INSTRUCTIONS = Path("AGENTS.md")
CLAUDE_ENTRYPOINT = Path("CLAUDE.md")
IMPORT_LINE = "@AGENTS.md"

REQUIRED_KEYS = (
    "slug",
    "description",
    "access",
    "web",
    "delegation",
    "reasoning-effort",
    "codex-model",
    "claude-model",
)
ACCESS_VALUES = {"read-only", "workspace-write"}
EFFORT_VALUES = {"low", "medium", "high", "xhigh", "max"}
DELEGATION_VALUES = {"none", "allowed"}
BOOL_VALUES = {"true", "false"}


def repository_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip())
    except (FileNotFoundError, subprocess.CalledProcessError):
        return Path.cwd()


def parse_definition(path: Path, label: Path = None) -> Tuple[Dict[str, str], str, List[str]]:
    """Return (metadata, body, problems) for one neutral agent definition."""
    problems: List[str] = []
    text = path.read_text(encoding="utf-8")
    path = label if label is not None else path
    if not text.startswith("---\n"):
        return {}, "", [f"{path}: does not start with a `---` frontmatter block."]
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {}, "", [f"{path}: frontmatter block is not closed by `---`."]

    meta: Dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ": " not in line:
            problems.append(f"{path}: cannot parse frontmatter line {line!r}.")
            continue
        key, value = line.split(": ", 1)
        meta[key.strip()] = value.strip()
    body = parts[2].strip()

    for key in REQUIRED_KEYS:
        if key not in meta:
            problems.append(f"{path}: missing required frontmatter key `{key}`.")
    if problems:
        return meta, body, problems

    if meta["slug"] != path.stem:
        problems.append(f"{path}: `slug` is {meta['slug']!r} but the filename is {path.stem!r}.")
    if not meta["description"]:
        problems.append(f"{path}: `description` is empty.")
    if meta["access"] not in ACCESS_VALUES:
        problems.append(f"{path}: `access` must be one of {sorted(ACCESS_VALUES)}.")
    if meta["reasoning-effort"] not in EFFORT_VALUES:
        problems.append(f"{path}: `reasoning-effort` must be one of {sorted(EFFORT_VALUES)}.")
    if meta["delegation"] not in DELEGATION_VALUES:
        problems.append(f"{path}: `delegation` must be one of {sorted(DELEGATION_VALUES)}.")
    if meta["web"] not in BOOL_VALUES:
        problems.append(f"{path}: `web` must be `true` or `false`.")
    if not body:
        problems.append(f"{path}: the instruction body is empty.")

    # Guard the emitters: these inputs cannot be represented in the target formats.
    if '"' in meta.get("description", ""):
        problems.append(f"{path}: `description` must not contain a double quote (breaks the Codex TOML string).")
    if '"""' in body:
        problems.append(f"{path}: the body must not contain `\"\"\"` (breaks the Codex TOML block).")

    return meta, body, problems


def claude_tools(meta: Dict[str, str]) -> List[str]:
    tools = ["Read", "Grep", "Glob"]
    if meta["access"] == "workspace-write":
        tools += ["Edit", "Write"]
    if meta["web"] == "true":
        tools += ["WebSearch", "WebFetch"]
    if meta["delegation"] == "allowed":
        tools.append("Agent")
    return tools


def render_codex(meta: Dict[str, str], body: str) -> str:
    return (
        'name = "{}"\n'
        'description = "{}"\n'
        'model = "{}"\n'
        'model_reasoning_effort = "{}"\n'
        'sandbox_mode = "{}"\n'
        'developer_instructions = """\n{}\n"""\n'
    ).format(
        meta["slug"].replace("-", "_"),
        meta["description"],
        meta["codex-model"],
        meta["reasoning-effort"],
        meta["access"],
        body,
    )


def render_claude(meta: Dict[str, str], body: str) -> str:
    return (
        "---\n"
        "name: {slug}\n"
        "description: {description}\n"
        "tools: {tools}\n"
        "model: {model}\n"
        "effort: {effort}\n"
        "---\n"
        "\n"
        "<!-- Generated from {source}/{slug}.md. Edit that file, then run check_tool_parity.py --write. -->\n"
        "\n"
        "{body}\n"
    ).format(
        slug=meta["slug"],
        description=meta["description"],
        tools=", ".join(claude_tools(meta)),
        model=meta["claude-model"],
        effort=meta["reasoning-effort"],
        source=NEUTRAL_AGENTS.as_posix(),
        body=body,
    )


def check_agents(root: Path, write: bool) -> Tuple[List[str], List[str]]:
    """Verify (or regenerate) the per-tool agent files."""
    problems: List[str] = []
    changes: List[str] = []

    neutral_dir = root / NEUTRAL_AGENTS
    if not neutral_dir.is_dir():
        return [f"{NEUTRAL_AGENTS}: directory is missing."], changes

    slugs = set()
    for source in sorted(neutral_dir.glob("*.md")):
        meta, body, issues = parse_definition(source, source.relative_to(root))
        if issues:
            problems.extend(issues)
            continue
        slugs.add(meta["slug"])

        targets = (
            (root / CODEX_AGENTS / (meta["slug"] + ".toml"), render_codex(meta, body)),
            (root / CLAUDE_AGENTS / (meta["slug"] + ".md"), render_claude(meta, body)),
        )
        for target, expected in targets:
            rel = target.relative_to(root)
            actual = target.read_text(encoding="utf-8") if target.is_file() else None
            if actual == expected:
                continue
            if write:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(expected, encoding="utf-8")
                changes.append(f"regenerated {rel}")
            elif actual is None:
                problems.append(f"{rel}: missing. Run check_tool_parity.py --write.")
            else:
                problems.append(f"{rel}: out of date. Run check_tool_parity.py --write.")

    # A tool-side agent with no neutral definition would only be seen by one tool.
    for directory, suffix in ((CODEX_AGENTS, ".toml"), (CLAUDE_AGENTS, ".md")):
        target_dir = root / directory
        if not target_dir.is_dir():
            continue
        for orphan in sorted(target_dir.glob("*" + suffix)):
            if orphan.stem not in slugs:
                problems.append(
                    "{}: has no definition in {}. Every agent must be defined once and generated for both tools.".format(
                        orphan.relative_to(root), NEUTRAL_AGENTS
                    )
                )
    return problems, changes


def check_skills(root: Path, write: bool) -> Tuple[List[str], List[str]]:
    """Verify (or repair) the Claude Code symlinks onto the shared skills."""
    problems: List[str] = []
    changes: List[str] = []

    shared_dir = root / SHARED_SKILLS
    claude_dir = root / CLAUDE_SKILLS
    if not shared_dir.is_dir():
        return [f"{SHARED_SKILLS}: directory is missing."], changes

    shared = sorted(p.name for p in shared_dir.iterdir() if (p / "SKILL.md").is_file())
    for name in shared:
        link = claude_dir / name
        expected_target = os.path.join("..", "..", SHARED_SKILLS.as_posix(), name)
        rel = link.relative_to(root)

        if not link.exists() and not link.is_symlink():
            if write:
                claude_dir.mkdir(parents=True, exist_ok=True)
                link.symlink_to(expected_target)
                changes.append(f"linked {rel}")
                continue
            problems.append(f"{rel}: missing. Codex sees this skill, Claude Code does not.")
            continue

        if not link.is_symlink():
            problems.append(f"{rel}: is a real directory, not a symlink. The two copies will diverge silently.")
            continue

        actual_target = os.readlink(link)
        if os.path.isabs(actual_target):
            problems.append(f"{rel}: points at the absolute path {actual_target!r}. Use a relative target.")
            continue
        if actual_target != expected_target:
            if write:
                link.unlink()
                link.symlink_to(expected_target)
                changes.append(f"relinked {rel}")
                continue
            problems.append(f"{rel}: points at {actual_target!r}, expected {expected_target!r}.")

    if claude_dir.is_dir():
        for entry in sorted(claude_dir.iterdir()):
            if entry.name not in shared:
                problems.append(
                    "{}: has no matching skill in {}.".format(entry.relative_to(root), SHARED_SKILLS)
                )
    return problems, changes


def check_instructions(root: Path) -> List[str]:
    """Verify that Claude Code still loads the shared repository instructions."""
    problems: List[str] = []
    instructions = root / INSTRUCTIONS
    entrypoint = root / CLAUDE_ENTRYPOINT

    if not instructions.is_file():
        problems.append(f"{INSTRUCTIONS}: missing. Both tools depend on it.")
    if not entrypoint.is_file():
        problems.append(f"{CLAUDE_ENTRYPOINT}: missing. Claude Code would load no repository instructions.")
        return problems

    lines = entrypoint.read_text(encoding="utf-8").splitlines()
    if not any(line.strip() == IMPORT_LINE for line in lines):
        problems.append(
            "{}: does not import {} on a line of its own. Claude Code would silently load no "
            "repository instructions.".format(CLAUDE_ENTRYPOINT, INSTRUCTIONS)
        )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the per-tool agent files and repair skill symlinks.",
    )
    parser.add_argument("--root", type=Path, default=None, help="Repository root to check.")
    args = parser.parse_args()

    root = (args.root or repository_root()).resolve()

    problems: List[str] = []
    changes: List[str] = []
    for collected in (check_agents(root, args.write), check_skills(root, args.write)):
        problems.extend(collected[0])
        changes.extend(collected[1])
    problems.extend(check_instructions(root))

    for change in changes:
        print(change)
    if problems:
        for problem in problems:
            print(f"ERROR {problem}", file=sys.stderr)
        print(
            "\nFAIL: {} parity problem(s).".format(len(problems)),
            file=sys.stderr,
        )
        return 1

    agent_count = len(list((root / NEUTRAL_AGENTS).glob("*.md")))
    skill_count = len([p for p in (root / SHARED_SKILLS).iterdir() if (p / "SKILL.md").is_file()])
    print(
        "OK: {} agent definition(s) generated for both tools, {} shared skill(s) visible to both tools.".format(
            agent_count, skill_count
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
