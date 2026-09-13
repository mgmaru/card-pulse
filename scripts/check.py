#!/usr/bin/env python3
"""Run Card Pulse quality checks with the pinned toolchain.

Every stage runs through ``uv run --locked`` so the local run and CI use the same
Python version, the same ``uv.lock``, and the same tool versions. Stages run in a
fixed order and a failing stage does not stop the following ones, so one run
reports every problem.

Usage:
    python3 scripts/check.py              # run every stage
    python3 scripts/check.py lint test    # run a subset
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections.abc import Sequence

STAGES: dict[str, list[str]] = {
    "format": ["ruff", "format", "--check"],
    "lint": ["ruff", "check"],
    "typecheck": ["mypy"],
    "test": ["pytest"],
}


def run_stage(name: str) -> bool:
    command = ["uv", "run", "--locked", "--", *STAGES[name]]
    print(f"\n== {name}: {' '.join(command)}", flush=True)
    return subprocess.run(command).returncode == 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Card Pulse quality checks with the pinned toolchain."
    )
    parser.add_argument(
        "stages",
        nargs="*",
        metavar="STAGE",
        help=f"stages to run, in any order (default: {' '.join(STAGES)})",
    )
    args = parser.parse_args(argv)

    unknown = [name for name in args.stages if name not in STAGES]
    if unknown:
        parser.error(f"unknown stage(s): {' '.join(unknown)}. Choose from: {' '.join(STAGES)}")

    if shutil.which("uv") is None:
        print("uv not found. See CONTRIBUTING.md for the setup steps.", file=sys.stderr)
        return 127

    # Keep the declared order regardless of how the stages were requested.
    selected = [name for name in STAGES if not args.stages or name in args.stages]
    results = {name: run_stage(name) for name in selected}

    print("\n== summary")
    for name, passed in results.items():
        print(f"{'pass' if passed else 'FAIL'}  {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
