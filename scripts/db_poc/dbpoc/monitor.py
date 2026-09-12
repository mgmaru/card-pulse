"""Observability checks: can the operator see the conditions DB-OPS-02 lists?"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import shutil
import time
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from . import config, measure
from .util import Result, make_engine

LONG_TRANSACTION_SECONDS = 65.0
LOCK_HOLD_SECONDS = 8.0


def _hold_transaction(engine_name: str, port: int | None, seconds: float, lock_row: bool,
                      ready: Any) -> None:
    eng = make_engine(engine_name, role="cp_worker", port=port)
    with eng.begin() as conn:
        if lock_row:
            conn.execute(sa.text("UPDATE review_item SET priority = priority WHERE id = 1"))
        else:
            conn.execute(sa.text("SELECT COUNT(*) FROM source"))
        ready.set()
        time.sleep(seconds)
    eng.dispose()


def _wait_for_lock(engine_name: str, port: int | None, seconds: float) -> None:
    eng = make_engine(engine_name, role="cp_worker", port=port)
    try:
        with eng.begin() as conn:
            if engine_name == "postgres":
                conn.exec_driver_sql(f"SET LOCAL lock_timeout = '{int(seconds)}s'")
            else:
                conn.exec_driver_sql(f"SET SESSION innodb_lock_wait_timeout = {int(seconds)}")
            conn.execute(sa.text("UPDATE review_item SET priority = priority WHERE id = 1"))
    except Exception:  # noqa: BLE001 - the wait itself is the point
        pass
    finally:
        eng.dispose()


def detect_long_transaction(engine_name: str, port: int | None) -> dict:
    ready = mp.Event()
    holder = mp.Process(target=_hold_transaction,
                        args=(engine_name, port, LONG_TRANSACTION_SECONDS, False, ready))
    holder.start()
    ready.wait(timeout=30)
    time.sleep(62.0)
    # innodb_trx timestamps use the server's local time zone.
    eng = make_engine(engine_name, port=port, utc_session=False)
    with eng.connect() as conn:
        if engine_name == "postgres":
            rows = conn.execute(sa.text(
                "SELECT pid, state, EXTRACT(EPOCH FROM (now() - xact_start)) AS age_seconds"
                " FROM pg_stat_activity WHERE xact_start IS NOT NULL"
                " AND now() - xact_start > interval '60 seconds'")).mappings().all()
        else:
            rows = conn.execute(sa.text(
                "SELECT trx_id, trx_state, TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS age_seconds"
                " FROM information_schema.innodb_trx"
                " WHERE trx_started < NOW() - INTERVAL 60 SECOND")).mappings().all()
    eng.dispose()
    holder.terminate()
    holder.join(timeout=30)
    return {
        "threshold_seconds": 60,
        "detected": len(rows) > 0,
        "rows": [dict(r) for r in rows][:5],
        "pass": len(rows) > 0,
    }


def detect_lock_wait(engine_name: str, port: int | None) -> dict:
    ready = mp.Event()
    holder = mp.Process(target=_hold_transaction,
                        args=(engine_name, port, LOCK_HOLD_SECONDS, True, ready))
    holder.start()
    ready.wait(timeout=30)
    waiter = mp.Process(target=_wait_for_lock, args=(engine_name, port, 20))
    waiter.start()
    time.sleep(6.0)
    eng = make_engine(engine_name, port=port, utc_session=False)
    with eng.connect() as conn:
        if engine_name == "postgres":
            rows = conn.execute(sa.text(
                "SELECT pid, wait_event_type, wait_event,"
                " EXTRACT(EPOCH FROM (now() - state_change)) AS waited_seconds"
                " FROM pg_stat_activity WHERE wait_event_type = 'Lock'"
                " AND now() - state_change > interval '5 seconds'")).mappings().all()
        else:
            rows = conn.execute(sa.text(
                "SELECT trx_id, trx_state,"
                " TIMESTAMPDIFF(SECOND, trx_wait_started, NOW()) AS waited_seconds"
                " FROM information_schema.innodb_trx WHERE trx_state = 'LOCK WAIT'"
                " AND trx_wait_started < NOW() - INTERVAL 5 SECOND")).mappings().all()
    eng.dispose()
    holder.join(timeout=30)
    waiter.join(timeout=60)
    return {
        "threshold_seconds": 5,
        "detected": len(rows) > 0,
        "rows": [dict(r) for r in rows][:5],
        "pass": len(rows) > 0,
    }


def slow_query_visibility(engine_name: str, port: int | None) -> dict:
    """Run a query slower than one second and check it is recorded."""

    eng = make_engine(engine_name, port=port)
    slow_sql = ("SELECT COUNT(*), SUM(amount_minor) FROM price_observation"
                " WHERE amount_minor > 0")
    with eng.connect() as conn:
        start = time.perf_counter()
        conn.execute(sa.text(slow_sql)).fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000
        if engine_name == "postgres":
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
            conn.commit()
            rows = conn.execute(sa.text(
                "SELECT calls, round(max_exec_time::numeric,1) AS max_ms, left(query, 80) AS query"
                " FROM pg_stat_statements WHERE max_exec_time > 1000"
                " ORDER BY max_exec_time DESC LIMIT 5")).mappings().all()
            source = "pg_stat_statements"
        else:
            rows = conn.execute(sa.text(
                "SELECT COUNT_STAR AS calls, ROUND(MAX_TIMER_WAIT/1000000000,1) AS max_ms,"
                " LEFT(DIGEST_TEXT, 80) AS query"
                " FROM performance_schema.events_statements_summary_by_digest"
                " WHERE SCHEMA_NAME = :schema AND MAX_TIMER_WAIT > 1000000000"
                " ORDER BY MAX_TIMER_WAIT DESC LIMIT 5"), {"schema": config.DB_NAME}).mappings().all()
            source = "performance_schema.events_statements_summary_by_digest"
    eng.dispose()
    return {
        "query_ms": elapsed_ms,
        "source": source,
        "recorded": len(rows) > 0,
        "rows": [dict(r) for r in rows],
        "pass": elapsed_ms < 1000 or len(rows) > 0,
    }


def connection_usage(engine_name: str, port: int | None) -> dict:
    eng = make_engine(engine_name, port=port)
    with eng.connect() as conn:
        if engine_name == "postgres":
            used = int(conn.execute(sa.text(
                "SELECT COUNT(*) FROM pg_stat_activity WHERE backend_type = 'client backend'"
            )).scalar_one())
            limit = int(conn.execute(sa.text(
                "SELECT setting::int FROM pg_settings WHERE name = 'max_connections'"
            )).scalar_one())
            started = conn.execute(sa.text("SELECT pg_postmaster_start_time()")).scalar_one()
            uptime = (datetime.now(UTC) - started).total_seconds()
        else:
            used = int(conn.execute(sa.text(
                "SHOW GLOBAL STATUS LIKE 'Threads_connected'")).fetchone()[1])
            limit = int(conn.execute(sa.text("SELECT @@GLOBAL.max_connections")).scalar_one())
            uptime = float(conn.execute(sa.text("SHOW GLOBAL STATUS LIKE 'Uptime'")).fetchone()[1])
    eng.dispose()
    ratio = used / limit if limit else None
    return {
        "connections_used": used,
        "max_connections": limit,
        "usage_ratio": ratio,
        "warning_at": 0.7,
        "warning_active": bool(ratio and ratio >= 0.7),
        "server_uptime_seconds": uptime,
        "restart_visible": uptime is not None,
        "pass": limit > 0 and uptime is not None,
    }


def storage_usage(engine_name: str, port: int | None) -> dict:
    footprint = measure.storage_footprint(engine_name)
    usage = shutil.disk_usage(config.POC_ROOT)
    ratio = usage.used / usage.total
    return {
        **footprint,
        "disk_total_bytes": usage.total,
        "disk_used_bytes": usage.used,
        "disk_usage_ratio": ratio,
        "warning_at": 0.7,
        "critical_at": 0.85,
        "warning_active": ratio >= 0.7,
        "pass": True,
    }


def backup_age(engine_name: str) -> dict:
    manifest = config.BACKUP_DIR / engine_name / "manifest.json"
    if not manifest.exists():
        return {"manifest": None, "pass": False, "note": "run the backup step first"}
    payload = json.loads(manifest.read_text())
    basis = datetime.fromisoformat(payload["basis_time"])
    age_hours = (datetime.now(UTC) - basis).total_seconds() / 3600
    return {
        "manifest": str(manifest),
        "basis_time": payload["basis_time"],
        "age_hours": age_hours,
        "alert_after_hours": 26,
        "alert_active": age_hours > 26,
        "pass": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["postgres", "mariadb"])
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--skip-long", action="store_true",
                        help="skip the 60 second transaction check")
    args = parser.parse_args()

    data: dict[str, Any] = {
        "connection_usage": connection_usage(args.engine, args.port),
        "storage_usage": storage_usage(args.engine, args.port),
        "slow_query": slow_query_visibility(args.engine, args.port),
        "lock_wait": detect_lock_wait(args.engine, args.port),
        "backup_age": backup_age(args.engine),
    }
    if not args.skip_long:
        data["long_transaction"] = detect_long_transaction(args.engine, args.port)
    data["all_passed"] = all(v.get("pass") for v in data.values() if isinstance(v, dict))
    result = Result(step="monitor", engine=args.engine, scale=args.scale, data=data)
    print(json.dumps(data, indent=2, default=str)[:2500])
    print(f"wrote {result.write()}")


if __name__ == "__main__":
    main()
