"""Size and plan measurements shared by the load and query steps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import sqlalchemy as sa

from . import config
from .schema import TABLE_ORDER
from .util import make_engine


def dir_bytes(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def table_sizes(engine: str, port: int | None = None,
                dbname: str = config.DB_NAME) -> dict[str, Any]:
    eng = make_engine(engine, port=port, dbname=dbname)
    out: dict[str, Any] = {"tables": {}}
    with eng.connect() as conn:
        if engine == "postgres":
            rows = conn.execute(sa.text(
                """
                SELECT c.relname AS table_name,
                       pg_table_size(c.oid) AS table_bytes,
                       pg_indexes_size(c.oid) AS index_bytes,
                       pg_total_relation_size(c.oid) AS total_bytes,
                       c.reltuples::bigint AS estimated_rows
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r'
                ORDER BY c.relname
                """
            )).mappings().all()
            for row in rows:
                out["tables"][row["table_name"]] = {
                    "table_bytes": int(row["table_bytes"]),
                    "index_bytes": int(row["index_bytes"]),
                    "total_bytes": int(row["total_bytes"]),
                }
            out["database_bytes"] = int(conn.execute(
                sa.text("SELECT pg_database_size(current_database())")).scalar_one())
        else:
            rows = conn.execute(sa.text(
                """
                SELECT table_name, data_length, index_length, data_free
                FROM information_schema.tables
                WHERE table_schema = :schema
                ORDER BY table_name
                """
            ), {"schema": dbname}).mappings().all()
            for row in rows:
                data = int(row["data_length"] or 0)
                index = int(row["index_length"] or 0)
                out["tables"][row["table_name"]] = {
                    "table_bytes": data,
                    "index_bytes": index,
                    "total_bytes": data + index,
                }
            out["database_bytes"] = sum(t["total_bytes"] for t in out["tables"].values())
    eng.dispose()
    out["table_bytes_total"] = sum(t["table_bytes"] for t in out["tables"].values())
    out["index_bytes_total"] = sum(t["index_bytes"] for t in out["tables"].values())
    return out


def storage_footprint(engine: str, instance: str = "main") -> dict[str, int]:
    """On-disk footprint including the database's own write-ahead or redo log."""

    if engine == "postgres":
        base = config.POC_ROOT / f"pg-{instance}" / "data"
        return {
            "data_dir_bytes": dir_bytes(base),
            "wal_bytes": dir_bytes(base / "pg_wal"),
        }
    base = config.POC_ROOT / f"maria-{instance}" / "data"
    redo = 0
    for name in ("ib_logfile0", "ib_logfile1"):
        candidate = base / name
        if candidate.exists():
            redo += candidate.stat().st_size
    return {"data_dir_bytes": dir_bytes(base), "wal_bytes": redo}


def row_counts(engine: str, port: int | None = None,
               dbname: str = config.DB_NAME) -> dict[str, int]:
    eng = make_engine(engine, port=port, dbname=dbname)
    counts: dict[str, int] = {}
    with eng.connect() as conn:
        for table in TABLE_ORDER:
            counts[table] = int(conn.execute(
                sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
    eng.dispose()
    return counts


def explain(engine: str, sql: str, params: dict[str, Any], port: int | None = None) -> str:
    eng = make_engine(engine, port=port)
    prefix = "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) " if engine == "postgres" else "EXPLAIN FORMAT=JSON "
    with eng.connect() as conn:
        rows = conn.execute(sa.text(prefix + sql), params).fetchall()
    eng.dispose()
    return "\n".join(str(row[0]) for row in rows)
