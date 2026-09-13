#!/usr/bin/env python3
"""Keep the committed branch ruleset and the one GitHub enforces in agreement.

The file under ``.github/rulesets/`` is the source of truth (ADR-0021). GitHub holds
the enforced copy, and nothing in this repository can change it on its own: ``apply``
is run by a person, never by CI. A workflow that could relax the rules protecting
``main`` would be reachable through ``main`` itself.

``check`` reads the enforced ruleset and reports every difference. It works without a
token on a public repository, which is what lets CI run it. ``bypass_actors`` is the
exception: GitHub withholds it from readers without write access, so the field is not
part of the committed file and is verified separately when a token is available.

Usage:
    python3 scripts/ruleset.py check     # compare, exit 1 on any difference
    python3 scripts/ruleset.py apply     # push the file to GitHub (people only)
    python3 scripts/ruleset.py export    # refresh the file from GitHub
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

RULESET_FILE = Path(".github/rulesets/main-protection.json")
DECLARED_FIELDS = ("name", "target", "enforcement", "conditions", "rules")
REMOTE_RE = re.compile(r"github\.com[:/](?P<repo>[^/]+/[^/]+?)(?:\.git)?$")


class RulesetError(RuntimeError):
    """Raised when the repository, the file, or the GitHub response is unusable."""


def repository() -> str:
    """Return ``owner/name`` from the Actions environment or the ``origin`` remote."""
    from_actions = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if from_actions:
        return from_actions
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise RulesetError("cannot determine the repository from git") from error
    match = REMOTE_RE.search(url)
    if match is None:
        raise RulesetError(f"cannot read owner/name from the origin remote: {url}")
    return match.group("repo")


def call_api(path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    """Call the GitHub API through ``gh``, which CI and the owner's machine both have."""
    command = ["gh", "api", "--method", method, path]
    if body is not None:
        command += ["--input", "-"]
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            input=json.dumps(body) if body is not None else None,
        )
    except FileNotFoundError as error:
        raise RulesetError("gh not found. See CONTRIBUTING.md for the setup steps.") from error
    except subprocess.CalledProcessError as error:
        raise RulesetError(f"{method} {path} failed: {error.stderr.strip()}") from error
    return json.loads(result.stdout) if result.stdout.strip() else None


def declared(ruleset: dict[str, Any]) -> dict[str, Any]:
    """Keep only the fields a person declares, with rules in a stable order."""
    kept = {field: ruleset[field] for field in DECLARED_FIELDS if field in ruleset}
    if "rules" in kept:
        kept["rules"] = sorted(kept["rules"], key=lambda rule: str(rule["type"]))
    return kept


def load_file(path: Path) -> dict[str, Any]:
    try:
        content: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RulesetError(f"{path} cannot be read: {error.strerror or error}") from error
    except json.JSONDecodeError as error:
        raise RulesetError(f"{path} is not valid JSON: {error}") from error
    missing = [field for field in DECLARED_FIELDS if field not in content]
    if missing:
        raise RulesetError(f"{path} is missing: {', '.join(missing)}")
    return content


def fetch(repo: str, name: str) -> tuple[int, dict[str, Any]] | None:
    """Return the identifier and body of the enforced ruleset with this name."""
    for summary in call_api(f"repos/{repo}/rulesets") or []:
        if summary["name"] == name:
            identifier = int(summary["id"])
            body: dict[str, Any] = call_api(f"repos/{repo}/rulesets/{identifier}")
            return identifier, body
    return None


def _by_type(rules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(rule["type"]): rule.get("parameters", {}) for rule in rules}


def _line(label: str, want: Any, have: Any) -> str:
    return (
        f"{label}:\n    committed: {json.dumps(want, ensure_ascii=False)}"
        f"\n    enforced:  {json.dumps(have, ensure_ascii=False)}"
    )


def differences(expected: dict[str, Any], enforced: dict[str, Any]) -> list[str]:
    """Report each declared field that GitHub enforces differently.

    Rules are compared one type at a time, so a report names the rule that moved
    instead of printing both lists in full.
    """
    want_all, have_all = declared(expected), declared(enforced)
    found = [
        _line(field, want_all.get(field), have_all.get(field))
        for field in DECLARED_FIELDS
        if field != "rules" and want_all.get(field) != have_all.get(field)
    ]

    want_rules = _by_type(want_all.get("rules", []))
    have_rules = _by_type(have_all.get("rules", []))
    for rule_type in sorted(set(want_rules) | set(have_rules)):
        if rule_type not in have_rules:
            found.append(f"rule {rule_type}: committed but not enforced")
        elif rule_type not in want_rules:
            found.append(f"rule {rule_type}: enforced but not committed")
        elif want_rules[rule_type] != have_rules[rule_type]:
            found.append(_line(f"rule {rule_type}", want_rules[rule_type], have_rules[rule_type]))
    return found


def check(repo: str, path: Path) -> int:
    expected = load_file(path)
    enforced = fetch(repo, expected["name"])
    if enforced is None:
        print(f"{repo} enforces no ruleset named {expected['name']!r}", file=sys.stderr)
        return 1
    _, body = enforced

    found = differences(expected, body)
    for difference in found:
        print(f"drift in {difference}", file=sys.stderr)

    # Only a reader with write access sees this field, so its absence is not a failure.
    if "bypass_actors" not in body:
        print("bypass_actors: not visible to this token, not checked")
    elif body["bypass_actors"]:
        print(f"bypass_actors: {json.dumps(body['bypass_actors'])} can bypass", file=sys.stderr)
        found.append("bypass_actors")
    else:
        print("bypass_actors: empty")

    if found:
        print(f"FAILED: {len(found)} difference(s) between {path} and {repo}.", file=sys.stderr)
        return 1
    print(f"OK: {repo} enforces {path} as written.")
    return 0


def apply(repo: str, path: Path) -> int:
    expected = load_file(path)
    enforced = fetch(repo, expected["name"])
    # An absent bypass_actors resets the list, which is the state this file describes.
    body = {**declared(expected), "bypass_actors": []}
    if enforced is None:
        call_api(f"repos/{repo}/rulesets", method="POST", body=body)
        print(f"created {expected['name']!r} on {repo}")
    else:
        identifier, _ = enforced
        call_api(f"repos/{repo}/rulesets/{identifier}", method="PUT", body=body)
        print(f"updated {expected['name']!r} ({identifier}) on {repo}")
    return check(repo, path)


def export(repo: str, path: Path) -> int:
    expected = load_file(path)
    enforced = fetch(repo, expected["name"])
    if enforced is None:
        print(f"{repo} enforces no ruleset named {expected['name']!r}", file=sys.stderr)
        return 1
    _, body = enforced
    path.write_text(json.dumps(declared(body), indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"wrote {path} from {repo}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("check", "apply", "export"))
    parser.add_argument(
        "--file",
        type=Path,
        default=RULESET_FILE,
        help=f"ruleset file to use (default: {RULESET_FILE})",
    )
    arguments = parser.parse_args(argv)

    commands = {"check": check, "apply": apply, "export": export}
    try:
        return commands[arguments.command](repository(), arguments.file)
    except RulesetError as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
