"""Connection, timing, and result helpers shared by the PoC steps."""

from __future__ import annotations

import json
import math
import os
import platform
import statistics
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import sqlalchemy as sa

from . import config

ENGINES = ("postgres", "mariadb")


def sqlalchemy_url(engine: str, role: str = "cp_admin", port: int | None = None,
                   dbname: str = config.DB_NAME) -> str:
    if engine == "postgres":
        port = port or config.PG_PORT
        return f"postgresql+psycopg://{role}:{config.ROLE_PASSWORD}@127.0.0.1:{port}/{dbname}"
    port = port or config.MARIA_PORT
    return f"mariadb+pymysql://{role}:{config.ROLE_PASSWORD}@127.0.0.1:{port}/{dbname}"


def make_engine(engine: str, role: str = "cp_admin", port: int | None = None,
                dbname: str = config.DB_NAME, utc_session: bool = True,
                **kwargs: Any) -> sa.Engine:
    """Create a SQLAlchemy engine with the same session semantics on both products.

    MariaDB has no timestamptz, so every session is pinned to UTC and the
    application stores UTC in ``DATETIME(6)``. Server metadata such as
    ``information_schema.innodb_trx`` is recorded in the server's local time
    instead, so monitoring queries pass ``utc_session=False`` and compare
    against the same clock.
    """

    url = sqlalchemy_url(engine, role, port, dbname)
    if engine == "postgres":
        connect_args = {"options": "-c timezone=UTC"} if utc_session else {}
    else:
        connect_args = {"local_infile": 1}
        if utc_session:
            connect_args["init_command"] = "SET time_zone='+00:00'"
    connect_args.update(kwargs.pop("connect_args", {}))
    return sa.create_engine(url, connect_args=connect_args, future=True, **kwargs)


def utcnow() -> datetime:
    return datetime.now(UTC)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[int(rank)]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min_ms": min(values),
        "median_ms": statistics.median(values),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "max_ms": max(values),
        "mean_ms": statistics.fmean(values),
    }


@dataclass
class Result:
    """One PoC step's measurements, written as JSON under var/db-poc/results."""

    step: str
    engine: str
    scale: int | None = None
    started_at: str = field(default_factory=lambda: utcnow().isoformat())
    data: dict[str, Any] = field(default_factory=dict)

    def path(self) -> Path:
        scale = "common" if self.scale is None else f"scale{self.scale}"
        directory = config.RESULT_DIR / self.engine / scale
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{self.step}.json"

    def write(self) -> Path:
        payload = {
            "step": self.step,
            "engine": self.engine,
            "scale": self.scale,
            "started_at": self.started_at,
            "finished_at": utcnow().isoformat(),
            **self.data,
        }
        target = self.path()
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return target


@contextmanager
def timer() -> Iterator[dict[str, float]]:
    box: dict[str, float] = {}
    start = time.perf_counter()
    try:
        yield box
    finally:
        box["seconds"] = time.perf_counter() - start


def run(cmd: list[str], env: dict[str, str] | None = None, check: bool = True,
        cwd: Path | None = None, stdout_path: Path | None = None) -> subprocess.CompletedProcess:
    merged = dict(os.environ)
    if env:
        merged.update(env)
    if stdout_path is not None:
        with stdout_path.open("wb") as handle:
            return subprocess.run(cmd, env=merged, check=check, cwd=cwd, stdout=handle,
                                  stderr=subprocess.PIPE)
    return subprocess.run(cmd, env=merged, check=check, cwd=cwd, capture_output=True, text=True)


def host_environment() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "memory_bytes": int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True,
                                           text=True).stdout.strip()),
        "python": platform.python_version(),
    }


def server_settings(engine: str, port: int | None = None) -> dict[str, Any]:
    """Capture the settings that make a measurement reproducible."""

    eng = make_engine(engine, port=port)
    out: dict[str, Any] = {}
    with eng.connect() as conn:
        if engine == "postgres":
            out["version"] = conn.execute(sa.text("SHOW server_version")).scalar_one()
            names = [
                "shared_buffers", "effective_cache_size", "work_mem", "maintenance_work_mem",
                "max_connections", "max_wal_size", "synchronous_commit", "random_page_cost",
                "default_transaction_isolation", "wal_level", "checkpoint_timeout",
            ]
            for name in names:
                out[name] = conn.execute(sa.text(f"SHOW {name}")).scalar_one()
        else:
            out["version"] = conn.execute(sa.text("SELECT VERSION()")).scalar_one()
            names = [
                "innodb_buffer_pool_size", "innodb_log_file_size", "innodb_flush_log_at_trx_commit",
                "max_connections", "sql_mode", "tx_isolation" if False else "transaction_isolation",
                "character_set_server", "collation_server", "innodb_lock_wait_timeout",
                "local_infile", "time_zone",
            ]
            for name in names:
                row = conn.execute(sa.text(f"SELECT @@GLOBAL.{name}")).scalar_one()
                out[name] = row
    eng.dispose()
    return out
