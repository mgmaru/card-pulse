#!/usr/bin/env python3
"""Validate stable task IDs, states, metadata, and dependencies in the roadmap."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


TASK_LINE_RE = re.compile(
    r"^- \[(?P<checked>[ xX])\] `(?P<id>CP-(?P<number>\d{4}))` "
    r"`(?P<status>[a-z-]+)` — (?P<title>\S.*)$"
)
CHECKBOX_RE = re.compile(r"^- \[[ xX]\]")
METADATA_RE = re.compile(
    r"^  - (?P<label>Depends on|Done when|Resume|Pause reason|Blocker|Resume when|Evidence|Cancellation reason):\s*(?P<value>.*)$"
)
TASK_ID_RE = re.compile(r"CP-\d{4}")
NEXT_ID_RE = re.compile(r"^> Next task ID: `CP-(?P<number>\d{4})`$")
ALLOWED_STATUSES = {
    "planned",
    "in-progress",
    "paused",
    "blocked",
    "done",
    "cancelled",
}
COMPLETED_STATUSES = {"done", "cancelled"}
REQUIRED_METADATA = {
    "in-progress": {"Resume"},
    "paused": {"Pause reason", "Resume"},
    "blocked": {"Blocker", "Resume when"},
    "done": {"Evidence"},
    "cancelled": {"Cancellation reason"},
}


@dataclass
class Task:
    identifier: str
    number: int
    status: str
    checked: bool
    title: str
    line: int
    metadata: dict[str, list[str]] = field(default_factory=dict)

    @property
    def dependencies(self) -> list[str]:
        values = self.metadata.get("Depends on", [])
        return [identifier for value in values for identifier in TASK_ID_RE.findall(value)]


def repository_root(start: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return start.resolve()
    return Path(result.stdout.strip()).resolve()


def parse_roadmap(path: Path) -> tuple[list[Task], int | None, list[str]]:
    tasks: list[Task] = []
    errors: list[str] = []
    current: Task | None = None
    next_number: int | None = None

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        next_id_match = NEXT_ID_RE.match(line)
        if next_id_match:
            if next_number is not None:
                errors.append(f"{path}:{line_number}: duplicate `Next task ID` counter")
            else:
                next_number = int(next_id_match.group("number"))
            current = None
            continue

        task_match = TASK_LINE_RE.match(line)
        if task_match:
            current = Task(
                identifier=task_match.group("id"),
                number=int(task_match.group("number")),
                status=task_match.group("status"),
                checked=task_match.group("checked").lower() == "x",
                title=task_match.group("title"),
                line=line_number,
            )
            tasks.append(current)
            continue

        if CHECKBOX_RE.match(line):
            errors.append(
                f"{path}:{line_number}: task does not match the canonical roadmap format"
            )
            current = None
            continue

        metadata_match = METADATA_RE.match(line)
        if metadata_match:
            if current is None:
                errors.append(
                    f"{path}:{line_number}: task metadata has no preceding roadmap task"
                )
                continue
            label = metadata_match.group("label")
            value = metadata_match.group("value").strip()
            if not value:
                errors.append(f"{path}:{line_number}: {label} must not be empty")
            current.metadata.setdefault(label, []).append(value)
            continue

        if line.startswith("  - ") and current is not None:
            errors.append(
                f"{path}:{line_number}: unknown task metadata label; "
                "use the labels documented by maintain-roadmap"
            )
        elif line and not line.startswith(" "):
            current = None

    if next_number is None:
        errors.append(f"{path}: missing `Next task ID` counter")

    return tasks, next_number, errors


def dependency_cycles(tasks_by_id: dict[str, Task]) -> list[list[str]]:
    cycles: list[list[str]] = []
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(identifier: str) -> None:
        if identifier in visiting:
            start = visiting.index(identifier)
            cycles.append(visiting[start:] + [identifier])
            return
        if identifier in visited:
            return
        visiting.append(identifier)
        for dependency in tasks_by_id[identifier].dependencies:
            if dependency in tasks_by_id:
                visit(dependency)
        visiting.pop()
        visited.add(identifier)

    for identifier in tasks_by_id:
        visit(identifier)
    return cycles


def validate(tasks: list[Task], next_number: int | None, path: Path) -> list[str]:
    errors: list[str] = []
    tasks_by_id: dict[str, Task] = {}

    for task in tasks:
        if task.identifier in tasks_by_id:
            errors.append(
                f"{path}:{task.line}: duplicate ID {task.identifier}; "
                f"first used at line {tasks_by_id[task.identifier].line}"
            )
        else:
            tasks_by_id[task.identifier] = task

        if task.status not in ALLOWED_STATUSES:
            errors.append(
                f"{path}:{task.line}: unsupported status `{task.status}`"
            )
        expected_checked = task.status in COMPLETED_STATUSES
        if task.checked != expected_checked:
            expected = "[x]" if expected_checked else "[ ]"
            errors.append(
                f"{path}:{task.line}: status `{task.status}` requires checkbox {expected}"
            )

        present_labels = {label for label, values in task.metadata.items() if any(values)}
        for label in REQUIRED_METADATA.get(task.status, set()) - present_labels:
            errors.append(
                f"{path}:{task.line}: status `{task.status}` requires `{label}` metadata"
            )

        if len(task.metadata.get("Depends on", [])) > 1:
            errors.append(
                f"{path}:{task.line}: combine dependencies into one `Depends on` entry"
            )

    for task in tasks:
        for dependency in task.dependencies:
            if dependency == task.identifier:
                errors.append(
                    f"{path}:{task.line}: {task.identifier} cannot depend on itself"
                )
            elif dependency not in tasks_by_id:
                errors.append(
                    f"{path}:{task.line}: dependency {dependency} does not exist"
                )
            elif task.status == "done" and tasks_by_id[dependency].status != "done":
                errors.append(
                    f"{path}:{task.line}: done task {task.identifier} depends on "
                    f"unfinished task {dependency}"
                )

    for cycle in dependency_cycles(tasks_by_id):
        errors.append(f"{path}: dependency cycle: {' -> '.join(cycle)}")

    if next_number is not None:
        highest_number = max((task.number for task in tasks), default=0)
        if next_number <= highest_number:
            errors.append(
                f"{path}: `Next task ID` must be greater than every allocated ID; "
                f"CP-{next_number:04d} is not greater than CP-{highest_number:04d}"
            )

    return errors


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the Card Pulse roadmap.")
    parser.add_argument(
        "--path",
        type=Path,
        help="Roadmap path. Defaults to docs/product/roadmap.md under the Git root.",
    )
    parser.add_argument(
        "--next-id",
        action="store_true",
        help="Print the next ID after validating the roadmap.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    root = repository_root(Path.cwd())
    path = (arguments.path or root / "docs/product/roadmap.md").resolve()
    if not path.exists():
        print(f"ERROR: roadmap does not exist: {path}")
        return 2

    tasks, next_number, parsing_errors = parse_roadmap(path)
    errors = parsing_errors + validate(tasks, next_number, path)
    if errors:
        for error in errors:
            print(error)
        print(f"FAILED: {len(errors)} roadmap problem(s).")
        return 1

    if arguments.next_id:
        assert next_number is not None
        print(f"CP-{next_number:04d}")
    else:
        print(f"OK: {len(tasks)} roadmap task(s) validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
