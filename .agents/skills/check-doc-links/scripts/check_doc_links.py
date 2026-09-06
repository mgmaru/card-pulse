#!/usr/bin/env python3
"""Validate repository-local links and heading anchors in Markdown files."""

from __future__ import annotations

import argparse
import html
import os
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


EXCLUDED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "var",
    "venv",
}

INLINE_LINK_RE = re.compile(
    r"!?\[[^\]]*\]\(\s*(?P<target><[^>]*>|[^)\s]+)"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)
REFERENCE_DEFINITION_RE = re.compile(
    r"^\s{0,3}\[[^\]]+\]:\s*(?P<target><[^>]*>|\S+)"
)
HTML_LINK_RE = re.compile(
    r"\b(?:href|src)\s*=\s*(?:\"(?P<double>[^\"]+)\"|'(?P<single>[^']+)')",
    re.IGNORECASE,
)
ATX_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(?P<text>.*?)(?:\s+#+\s*)?$")
SETEXT_HEADING_RE = re.compile(r"^\s{0,3}(?:=+|-+)\s*$")
EXPLICIT_ANCHOR_RE = re.compile(
    r"<[^>]+\b(?:id|name)\s*=\s*(?:\"([^\"]+)\"|'([^']+)')[^>]*>",
    re.IGNORECASE,
)
INLINE_CODE_RE = re.compile(r"`+[^`]*`+")
MARKDOWN_LINK_LABEL_RE = re.compile(r"!?\[([^\]]+)\]\([^)]*\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Link:
    source: Path
    line: int
    target: str


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


def markdown_files(root: Path, requested: list[str]) -> list[Path]:
    starts = [root / item for item in requested] if requested else [root]
    found: set[Path] = set()

    for start in starts:
        resolved = start.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise ValueError(f"requested path escapes repository root: {start}") from error
        if not resolved.exists():
            raise ValueError(f"requested path does not exist: {start}")
        if resolved.is_file():
            if resolved.suffix.lower() in {".md", ".markdown"}:
                found.add(resolved)
            continue

        for directory, names, files in os.walk(resolved):
            names[:] = sorted(name for name in names if name not in EXCLUDED_DIRECTORIES)
            base = Path(directory)
            for name in sorted(files):
                candidate = base / name
                if candidate.suffix.lower() in {".md", ".markdown"}:
                    found.add(candidate.resolve())

    return sorted(found)


def active_lines(text: str) -> list[str | None]:
    output: list[str | None] = []
    fence_character: str | None = None
    fence_length = 0

    for line in text.splitlines():
        stripped = line.lstrip()
        fence = re.match(r"(`{3,}|~{3,})", stripped)
        if fence_character is None and fence:
            fence_character = fence.group(1)[0]
            fence_length = len(fence.group(1))
            output.append(None)
            continue
        if fence_character is not None:
            if re.match(rf"{re.escape(fence_character)}{{{fence_length},}}\s*$", stripped):
                fence_character = None
                fence_length = 0
            output.append(None)
            continue
        output.append(line)

    return output


def extract_links(path: Path, text: str) -> list[Link]:
    links: list[Link] = []
    for line_number, line in enumerate(active_lines(text), start=1):
        if line is None:
            continue
        searchable = INLINE_CODE_RE.sub("", line)
        for match in INLINE_LINK_RE.finditer(searchable):
            links.append(Link(path, line_number, normalize_destination(match.group("target"))))
        definition = REFERENCE_DEFINITION_RE.match(searchable)
        if definition:
            links.append(
                Link(path, line_number, normalize_destination(definition.group("target")))
            )
        for match in HTML_LINK_RE.finditer(searchable):
            links.append(
                Link(path, line_number, match.group("double") or match.group("single"))
            )
    return links


def normalize_destination(target: str) -> str:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    return html.unescape(target)


def heading_slug(text: str) -> str:
    text = MARKDOWN_LINK_LABEL_RE.sub(r"\1", text)
    text = INLINE_CODE_RE.sub(lambda match: match.group(0).strip("`"), text)
    text = HTML_TAG_RE.sub("", text)
    text = html.unescape(text).strip().lower()

    characters: list[str] = []
    for character in text:
        category = unicodedata.category(character)
        if character in {"-", "_", " "} or category[0] in {"L", "N", "M"}:
            characters.append(character)
    return re.sub(r"\s+", "-", "".join(characters))


def anchors(path: Path, cache: dict[Path, set[str]]) -> set[str]:
    if path in cache:
        return cache[path]

    text = path.read_text(encoding="utf-8")
    lines = active_lines(text)
    result: set[str] = set()
    duplicate_counts: dict[str, int] = defaultdict(int)

    def add_heading(value: str) -> None:
        base = heading_slug(value)
        if not base:
            return
        count = duplicate_counts[base]
        duplicate_counts[base] += 1
        result.add(base if count == 0 else f"{base}-{count}")

    previous_line: str | None = None
    for line in lines:
        if line is None:
            previous_line = None
            continue
        atx = ATX_HEADING_RE.match(line)
        if atx:
            add_heading(atx.group("text"))
        elif SETEXT_HEADING_RE.match(line) and previous_line and previous_line.strip():
            add_heading(previous_line.strip())
        for match in EXPLICIT_ANCHOR_RE.finditer(line):
            result.add(html.unescape(match.group(1) or match.group(2)))
        previous_line = line

    cache[path] = result
    return result


def exact_case_exists(root: Path, path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root)
    except ValueError:
        return False

    current = root
    for part in relative.parts:
        try:
            names = {child.name for child in current.iterdir()}
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            return False
        if part not in names:
            return False
        current /= part
    return True


def validate_link(
    link: Link, root: Path, anchor_cache: dict[Path, set[str]]
) -> str | None:
    if not link.target:
        return None

    parsed = urlsplit(link.target)
    if parsed.scheme:
        if parsed.scheme.lower() == "file":
            return "file:// links are not portable; use a repository-relative link"
        return None
    if link.target.startswith("//"):
        return None

    relative_path = unquote(parsed.path)
    fragment = unquote(parsed.fragment)

    if relative_path.startswith("/"):
        return "absolute links are not portable; use a repository-relative link"

    destination = link.source if not relative_path else link.source.parent / relative_path
    resolved = destination.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return f"target escapes repository root: {relative_path}"

    if not resolved.exists() or not exact_case_exists(root, resolved):
        return f"target does not exist with exact case: {relative_path or '.'}"

    if fragment and resolved.is_file() and resolved.suffix.lower() in {".md", ".markdown"}:
        if fragment not in anchors(resolved, anchor_cache):
            return f"heading anchor does not exist: #{fragment}"

    return None


def is_remote_target(target: str) -> bool:
    parsed = urlsplit(target)
    return (bool(parsed.scheme) and parsed.scheme.lower() != "file") or target.startswith(
        "//"
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check repository-local Markdown links and heading anchors."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional Markdown files or directories relative to the repository root.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        help="Repository root. Defaults to the current Git repository root.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    root = (arguments.root or repository_root(Path.cwd())).resolve()
    if not root.is_dir():
        print(f"ERROR: repository root is not a directory: {root}", file=sys.stderr)
        return 2

    try:
        files = markdown_files(root, arguments.paths)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    errors: list[str] = []
    checked_links = 0
    skipped_remote_links = 0
    anchor_cache: dict[Path, set[str]] = {}

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            errors.append(f"{path.relative_to(root)}: invalid UTF-8: {error}")
            continue
        for link in extract_links(path, text):
            if is_remote_target(link.target):
                skipped_remote_links += 1
                continue
            checked_links += 1
            problem = validate_link(link, root, anchor_cache)
            if problem:
                errors.append(
                    f"{link.source.relative_to(root)}:{link.line}: "
                    f"{problem} ({link.target})"
                )

    if errors:
        for error in errors:
            print(error)
        print(
            f"FAILED: {len(errors)} problem(s) across {len(files)} Markdown file(s); "
            f"checked {checked_links} local link occurrence(s), "
            f"skipped {skipped_remote_links} remote link occurrence(s)."
        )
        return 1

    print(
        f"OK: {len(files)} Markdown file(s), {checked_links} local link occurrence(s) "
        f"checked, {skipped_remote_links} remote link occurrence(s) skipped."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
