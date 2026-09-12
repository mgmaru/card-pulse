"""Failure injection: a killed client process and a killed database server.

Confirms that no partial rows survive an interrupted transaction and that rows
committed before a crash are still present after recovery (PoC condition 5).
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa

from . import config
from .util import Result, make_engine, timer
from .workload import (ID_BASE, WRITER_STRIDE, build_batch, insert_observations, next_sequence,
                       write_batch)

INSTANCES = Path(__file__).resolve().parents[2] / "db_poc" / "bin" / "instances.sh"
CRASH_WRITER = 60


def _marker_rows(engine_name: str, port: int | None, marker: str) -> int:
    eng = make_engine(engine_name, port=port)
    with eng.connect() as conn:
        count = int(conn.execute(sa.text(
            "SELECT COUNT(*) FROM price_observation WHERE idempotency_key LIKE :m"),
            {"m": f"{marker}%"}).scalar_one())
    eng.dispose()
    return count


def _rows_for(engine_name: str, eng: sa.Engine, marker: str, base_id: int, count: int) -> list[dict]:
    batch = build_batch(CRASH_WRITER, base_id % 1_000_000, count, config.PROFILES[1].cards,
                        tag="crash")
    with eng.connect() as conn:
        candidate_id = conn.execute(sa.text(
            "SELECT id FROM observation_candidate ORDER BY id LIMIT 1")).scalar_one()
        artifact_id = conn.execute(sa.text(
            "SELECT id FROM raw_artifact ORDER BY id LIMIT 1")).scalar_one()
    rows = []
    for index, row in enumerate(batch["price_observation"]):
        row = dict(row)
        row["id"] = base_id + index
        row["observation_candidate_id"] = candidate_id
        row["raw_artifact_id"] = artifact_id
        row["idempotency_key"] = f"{marker}-{index}"
        rows.append(row)
    return rows


def _uncommitted_holder(engine_name: str, port: int | None, marker: str, base_id: int,
                        count: int, ready: Any) -> None:
    """Insert rows, never commit, and wait to be killed."""

    eng = make_engine(engine_name, role="cp_worker", port=port)
    rows = _rows_for(engine_name, eng, marker, base_id, count)
    with eng.connect() as conn:
        conn.begin()
        insert_observations(conn, engine_name, rows, idempotent=False)
        ready.set()
        time.sleep(120)


def check_killed_client(engine_name: str, port: int | None) -> dict:
    marker = f"poc-crash-client-{uuid.uuid4().hex[:8]}"
    base_id = ID_BASE["price_observation"] + CRASH_WRITER * WRITER_STRIDE + int(time.time()) % 100000 * 100
    ready = mp.Event()
    holder = mp.Process(target=_uncommitted_holder,
                        args=(engine_name, port, marker, base_id, 25, ready))
    holder.start()
    ready.wait(timeout=60)
    time.sleep(0.5)
    holder.kill()
    holder.join(timeout=30)
    time.sleep(2.0)  # let the server notice the closed connection
    remaining = _marker_rows(engine_name, port, marker)
    return {
        "inserted_before_kill": 25,
        "rows_after_kill": remaining,
        "pass": remaining == 0,
    }


def check_server_crash(engine_name: str, port: int | None, instance: str = "main") -> dict:
    """Kill the server with committed and uncommitted work in flight."""

    committed_marker = f"poc-crash-committed-{uuid.uuid4().hex[:8]}"
    pending_marker = f"poc-crash-pending-{uuid.uuid4().hex[:8]}"
    stamp = int(time.time()) % 100000 * 100
    base = ID_BASE["price_observation"] + CRASH_WRITER * WRITER_STRIDE + stamp

    eng = make_engine(engine_name, role="cp_worker", port=port)
    committed_rows = _rows_for(engine_name, eng, committed_marker, base + 1000, 25)
    with eng.begin() as conn:
        insert_observations(conn, engine_name, committed_rows, idempotent=False)
    eng.dispose()

    ready = mp.Event()
    holder = mp.Process(target=_uncommitted_holder,
                        args=(engine_name, port, pending_marker, base + 2000, 25, ready))
    holder.start()
    ready.wait(timeout=60)
    time.sleep(0.5)

    kill_command = "pg-kill" if engine_name == "postgres" else "maria-kill"
    start_command = "pg-start" if engine_name == "postgres" else "maria-start"
    kill = subprocess.run([str(INSTANCES), kill_command, instance], capture_output=True, text=True)
    holder.kill()
    holder.join(timeout=30)
    time.sleep(2.0)
    with timer() as recovery:
        start = subprocess.run([str(INSTANCES), start_command, instance], capture_output=True,
                               text=True)
    committed_after = _marker_rows(engine_name, port, committed_marker)
    pending_after = _marker_rows(engine_name, port, pending_marker)
    return {
        "kill_output": (kill.stdout + kill.stderr).strip()[:300],
        "restart_output": (start.stdout + start.stderr).strip()[:300],
        "recovery_seconds": recovery["seconds"],
        "committed_rows_before_crash": 25,
        "committed_rows_after_restart": committed_after,
        "uncommitted_rows_after_restart": pending_after,
        "pass": committed_after == 25 and pending_after == 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["postgres", "mariadb"])
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    data: dict[str, Any] = {}
    data["killed_client"] = check_killed_client(args.engine, args.port)
    print(f"  killed_client: {data['killed_client']}", flush=True)
    data["server_crash"] = check_server_crash(args.engine, args.port)
    print(f"  server_crash: {data['server_crash']}", flush=True)
    data["all_passed"] = all(v.get("pass") for v in data.values() if isinstance(v, dict))
    result = Result(step="crash", engine=args.engine, scale=args.scale, data=data)
    print(json.dumps(data, indent=2, default=str)[:2000])
    print(f"wrote {result.write()}")


if __name__ == "__main__":
    main()
