"""Run the whole PoC sequence for one candidate and one profile.

Each step runs as its own process and writes its own result file, so a failed
step is visible without discarding the steps that already finished.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from . import config
from .util import Result, host_environment, server_settings

HARNESS_DIR = Path(__file__).resolve().parents[1]
INSTANCES = HARNESS_DIR / "bin" / "instances.sh"
PYTHON = HARNESS_DIR / ".venv" / "bin" / "python"


def run_step(name: str, args: list[str], timeout: float = 36_000) -> dict:
    start = time.perf_counter()
    proc = subprocess.run([str(PYTHON), "-m", *args], cwd=HARNESS_DIR, capture_output=True,
                          text=True, timeout=timeout)
    seconds = time.perf_counter() - start
    status = "ok" if proc.returncode == 0 else "failed"
    print(f"[{status}] {name} ({seconds:.1f}s)", flush=True)
    if proc.returncode != 0:
        print(proc.stderr[-1500:], flush=True)
    return {
        "step": name,
        "command": " ".join(args),
        "returncode": proc.returncode,
        "seconds": seconds,
        "stdout_tail": proc.stdout[-800:],
        "stderr_tail": proc.stderr[-800:],
    }


def restart(engine: str, instance: str = "main") -> float:
    """Restart the server so the next measurement starts with cold caches."""

    stop = "pg-stop" if engine == "postgres" else "maria-stop"
    start = "pg-start" if engine == "postgres" else "maria-start"
    subprocess.run([str(INSTANCES), stop, instance], check=False, capture_output=True)
    began = time.perf_counter()
    subprocess.run([str(INSTANCES), start, instance], check=True, capture_output=True)
    return time.perf_counter() - began


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["postgres", "mariadb"])
    parser.add_argument("--scale", type=int, choices=[1, 10], required=True)
    parser.add_argument("--bench-seconds", type=float, default=180.0)
    parser.add_argument("--reparse-artifacts", type=int, default=None)
    parser.add_argument("--skip", nargs="*", default=[])
    args = parser.parse_args()

    engine = args.engine
    scale = str(args.scale)
    steps: list[dict] = []
    began = time.perf_counter()

    def maybe(name: str, argv: list[str], **kwargs) -> None:
        if name in args.skip:
            print(f"[skip] {name}", flush=True)
            return
        steps.append(run_step(name, argv, **kwargs))

    maybe("roles-create", ["dbpoc.bootstrap", engine, "--step", "roles"])
    maybe("reset", ["dbpoc.bootstrap", engine, "--step", "reset"])
    maybe("migrate-initial", ["dbpoc.migrate", engine, "--step", "initial"])
    maybe("migrate-offline", ["dbpoc.migrate", engine, "--step", "offline"])
    maybe("grants", ["dbpoc.bootstrap", engine, "--step", "grants"])
    maybe("seed", ["dbpoc.bootstrap", engine, "--step", "seed"])
    maybe("load", ["dbpoc.load", engine, "--scale", scale])
    maybe("ingest-daily", ["dbpoc.ingest", engine, "--scale", scale, "--step", "daily"])

    if "bench-cold" not in args.skip:
        restart_seconds = restart(engine)
        steps.append({"step": "restart-for-cold-cache", "seconds": restart_seconds,
                      "returncode": 0, "command": "instances.sh restart"})
        maybe("bench-cold", ["dbpoc.bench", engine, "--scale", scale, "--cold"])

    maybe("bench", ["dbpoc.bench", engine, "--scale", scale,
                    "--seconds", str(args.bench_seconds)])
    maybe("integrity", ["dbpoc.integrity", engine, "--scale", scale])
    maybe("crash", ["dbpoc.crash", engine, "--scale", scale])
    reparse_argv = ["dbpoc.ingest", engine, "--scale", scale, "--step", "reparse"]
    if args.reparse_artifacts:
        reparse_argv += ["--artifacts", str(args.reparse_artifacts)]
    maybe("ingest-reparse", reparse_argv)
    maybe("migrate-compat", ["dbpoc.migrate", engine, "--scale", scale, "--step", "compat"])
    maybe("migrate-failing", ["dbpoc.migrate", engine, "--step", "failing"])
    maybe("roles", ["dbpoc.roles", engine, "--scale", scale])
    maybe("backup", ["dbpoc.backup", engine, "--scale", scale, "--step", "backup"])
    maybe("restore", ["dbpoc.backup", engine, "--scale", scale, "--step", "restore"])
    maybe("monitor", ["dbpoc.monitor", engine, "--scale", scale])
    # Last, because a failed downgrade can leave the schema partially reverted
    # on a database without transactional DDL.
    maybe("migrate-downgrade", ["dbpoc.migrate", engine, "--step", "downgrade"])

    summary = Result(step="run-all", engine=engine, scale=args.scale, data={
        "total_seconds": time.perf_counter() - began,
        "steps": steps,
        "failed_steps": [s["step"] for s in steps if s["returncode"] != 0],
        "host": host_environment(),
        "server_settings": server_settings(engine),
    })
    path = summary.write()
    print(f"\nfinished in {(time.perf_counter() - began) / 60:.1f} min; summary at {path}")
    failed = [s["step"] for s in steps if s["returncode"] != 0]
    if failed:
        print(f"failed steps: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
