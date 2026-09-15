#!/usr/bin/env python3
"""Check that every ADR keeps the shape `docs/adr/README.md` defines.

The rules being enforced are structural: which sections exist and in what order,
which header fields exist and in what order, which status values are allowed, that a
supersession is recorded on both ADRs, and that the index table agrees with the files.
Readability rules from the same README, such as sentence length, stay with the author -
a sentence can be long and clear, so a machine that rejects it would be wrong.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ADR_DIRECTORY = Path("docs/adr")
INDEX = ADR_DIRECTORY / "README.md"
FILE_NAME = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")
TITLE = re.compile(r"^# ADR-(\d{4}): .+$")
HEADER_FIELD = re.compile(r"^- ([^:]+): ?(.*)$")
SECTION = re.compile(r"^## (.+)$", re.MULTILINE)
SUBSECTION_OWNER = "Decision"
ADR_REFERENCE = re.compile(r"ADR-(\d{4})")

SECTIONS = ("Context", "Decision", "Consequences", "Alternatives considered", "Validation")
FIELDS = ("状態", "日付", "決定者", "置換するADR", "置換されたADR")
STATUSES = ("Proposed", "Accepted", "Rejected", "Superseded", "Deprecated")
NONE = "なし"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# `置換するADR` names the older ADR this one replaced; `置換されたADR` names the newer
# one that replaced this. A pair has to appear on both sides, pointing at each other.
SUPERSEDES, SUPERSEDED_BY = FIELDS[3], FIELDS[4]


def repository_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ADR_DIRECTORY).is_dir():
            return candidate
    raise SystemExit(f"{ADR_DIRECTORY} not found from {start}")


def parse(path: Path) -> tuple[dict[str, str], list[str], list[str]]:
    """Return the header fields, the section names in order, and any parse errors."""
    errors: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()

    if not lines or not TITLE.match(lines[0]):
        errors.append(f"{path}:1: title is not `# ADR-NNNN: <判断のタイトル>`")
    elif (match := TITLE.match(lines[0])) and match.group(1) != path.name[:4]:
        errors.append(f"{path}:1: title says ADR-{match.group(1)} but the file is {path.name[:4]}")

    fields: dict[str, str] = {}
    order: list[str] = []
    for number, line in enumerate(lines, start=1):
        if line.startswith("## "):
            break
        if field := HEADER_FIELD.match(line):
            name, value = field.group(1), field.group(2).strip()
            if name in fields:
                errors.append(f"{path}:{number}: header field `{name}` appears twice")
            fields[name] = value
            order.append(name)

    if order != list(FIELDS):
        errors.append(
            f"{path}: header fields are {order or '[]'}; "
            f"the README requires exactly {list(FIELDS)} in this order"
        )

    sections = SECTION.findall("\n".join(lines))
    if sections != list(SECTIONS):
        errors.append(
            f"{path}: sections are {sections}; "
            f"the README requires exactly {list(SECTIONS)} in this order"
        )

    current = None
    for number, line in enumerate(lines, start=1):
        if line.startswith("## "):
            current = line[3:].strip()
        elif line.startswith("### ") and current != SUBSECTION_OWNER:
            errors.append(f"{path}:{number}: `###` is only allowed inside `{SUBSECTION_OWNER}`")

    return fields, sections, errors


def check_values(path: Path, fields: dict[str, str]) -> list[str]:
    errors = []
    status = fields.get(FIELDS[0], "")
    if status not in STATUSES:
        errors.append(f"{path}: 状態 is `{status}`; allowed values are {list(STATUSES)}")
    date = fields.get(FIELDS[1], "")
    if not DATE.match(date):
        errors.append(f"{path}: 日付 is `{date}`; expected YYYY-MM-DD")
    for name in FIELDS[2:]:
        if not fields.get(name):
            errors.append(f"{path}: {name} is empty; write `{NONE}` when there is none")
    return errors


def referenced(value: str) -> set[str]:
    return set() if value == NONE else set(ADR_REFERENCE.findall(value))


def check_supersession(headers: dict[str, dict[str, str]]) -> list[str]:
    errors = []
    for number, fields in sorted(headers.items()):
        replaced = referenced(fields.get(SUPERSEDES, NONE))
        replaced_by = referenced(fields.get(SUPERSEDED_BY, NONE))
        if both := replaced & replaced_by:
            errors.append(f"ADR-{number}: {sorted(both)} appears in both supersession fields")
        for other in replaced:
            if other not in headers:
                errors.append(f"ADR-{number}: {SUPERSEDES} names ADR-{other}, which does not exist")
            elif number not in referenced(headers[other].get(SUPERSEDED_BY, NONE)):
                errors.append(
                    f"ADR-{number}: {SUPERSEDES} names ADR-{other}, "
                    f"but ADR-{other} does not name ADR-{number} in {SUPERSEDED_BY}"
                )
            elif headers[other].get(FIELDS[0]) != "Superseded":
                errors.append(
                    f"ADR-{other}: replaced by ADR-{number} but 状態 is "
                    f"`{headers[other].get(FIELDS[0])}`, not `Superseded`"
                )
        for other in replaced_by:
            if other not in headers:
                errors.append(
                    f"ADR-{number}: {SUPERSEDED_BY} names ADR-{other}, which does not exist"
                )
            elif number not in referenced(headers[other].get(SUPERSEDES, NONE)):
                errors.append(
                    f"ADR-{number}: {SUPERSEDED_BY} names ADR-{other}, "
                    f"but ADR-{other} does not name ADR-{number} in {SUPERSEDES}"
                )
    return errors


def check_index(root: Path, headers: dict[str, dict[str, str]]) -> list[str]:
    errors = []
    text = (root / INDEX).read_text(encoding="utf-8")
    rows = dict(re.findall(r"^\| \[(\d{4})\]\([^)]+\) \| ([A-Za-z]+) \|", text, re.MULTILINE))
    for number in sorted(set(headers) | set(rows)):
        if number not in rows:
            errors.append(f"{INDEX}: ADR-{number} is missing from the index table")
        elif number not in headers:
            errors.append(f"{INDEX}: the index table lists ADR-{number}, which has no file")
        elif rows[number] != headers[number].get(FIELDS[0]):
            errors.append(
                f"{INDEX}: ADR-{number} is listed as `{rows[number]}` "
                f"but the file says `{headers[number].get(FIELDS[0])}`"
            )
    return errors


def main() -> int:
    root = repository_root(Path.cwd().resolve())
    paths = sorted(p for p in (root / ADR_DIRECTORY).glob("*.md") if FILE_NAME.match(p.name))
    if not paths:
        print(f"FAILED: no ADR found under {ADR_DIRECTORY}.")
        return 1

    errors: list[str] = []
    headers: dict[str, dict[str, str]] = {}
    for path in paths:
        fields, _, problems = parse(path)
        errors.extend(problems)
        errors.extend(check_values(path.relative_to(root), fields))
        headers[path.name[:4]] = fields

    errors.extend(check_supersession(headers))
    errors.extend(check_index(root, headers))

    if errors:
        for error in errors:
            print(error)
        print(f"FAILED: {len(errors)} ADR problem(s) across {len(paths)} ADR(s).")
        return 1

    print(f"OK: {len(paths)} ADR(s) validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
