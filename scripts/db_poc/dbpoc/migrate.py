"""Alembic migration behaviour on both candidates.

Covers PoC conditions 1 and 7: applying migrations to an empty database and to
an existing schema, offline SQL generation, a failing multi-statement
migration, and how a partially applied migration is identified and repaired.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import sqlalchemy as sa

from . import config
from .util import Result, make_engine, percentile, timer

HARNESS_DIR = Path(__file__).resolve().parents[1]


def alembic_url(engine: str, port: int | None = None, role: str = "cp_migration") -> str:
    if engine == "postgres":
        port = port or config.PG_PORT
        return (f"postgresql+psycopg://{role}:{config.ROLE_PASSWORD}@127.0.0.1:{port}"
                f"/{config.DB_NAME}")
    port = port or config.MARIA_PORT
    return (f"mariadb+pymysql://{role}:{config.ROLE_PASSWORD}@127.0.0.1:{port}/{config.DB_NAME}")


def run_alembic(engine: str, args: list[str], port: int | None = None,
                stdout_path: Path | None = None, lock_timeout_seconds: int | None = None) -> dict:
    env = dict(os.environ, POC_DSN=alembic_url(engine, port))
    if lock_timeout_seconds and engine == "postgres":
        # Without this a migration waits behind any open transaction and every
        # later writer queues behind the migration.
        env["PGOPTIONS"] = f"-c lock_timeout={lock_timeout_seconds}s"
    start = time.perf_counter()
    if stdout_path is not None:
        with stdout_path.open("w") as handle:
            proc = subprocess.run([".venv/bin/alembic", *args], cwd=HARNESS_DIR, env=env,
                                  stdout=handle, stderr=subprocess.PIPE, text=True)
        stdout = f"(written to {stdout_path})"
    else:
        proc = subprocess.run([".venv/bin/alembic", *args], cwd=HARNESS_DIR, env=env,
                              capture_output=True, text=True)
        stdout = proc.stdout
    return {
        "command": " ".join(args),
        "returncode": proc.returncode,
        "seconds": time.perf_counter() - start,
        "stdout": stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def current_revision(engine: str, port: int | None = None) -> str | None:
    eng = make_engine(engine, port=port)
    with eng.connect() as conn:
        try:
            value = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
        except sa.exc.DatabaseError:
            value = None
    eng.dispose()
    return value


def object_state(engine: str, port: int | None = None) -> dict[str, bool]:
    """Which objects from the failing migration 0003 exist right now."""

    eng = make_engine(engine, port=port)
    inspector = sa.inspect(eng)
    tables = set(inspector.get_table_names())
    columns = {c["name"] for c in inspector.get_columns("review_item")}
    indexes = {i["name"] for i in inspector.get_indexes("price_observation")}
    eng.dispose()
    return {
        "review_item.triage_note": "triage_note" in columns,
        "migration_probe": "migration_probe" in tables,
        "ix_observation_card_unique": "ix_observation_card_unique" in indexes,
    }


def repair_partial(engine: str, port: int | None = None) -> list[str]:
    """Undo objects left behind by a partially applied migration."""

    actions: list[str] = []
    state = object_state(engine, port)
    eng = make_engine(engine, role="cp_migration", port=port, isolation_level="AUTOCOMMIT")
    with eng.connect() as conn:
        if state["ix_observation_card_unique"]:
            conn.exec_driver_sql("DROP INDEX ix_observation_card_unique ON price_observation"
                                 if engine == "mariadb"
                                 else "DROP INDEX ix_observation_card_unique")
            actions.append("dropped ix_observation_card_unique")
        if state["migration_probe"]:
            conn.exec_driver_sql("DROP TABLE migration_probe")
            actions.append("dropped migration_probe")
        if state["review_item.triage_note"]:
            conn.exec_driver_sql("ALTER TABLE review_item DROP COLUMN triage_note")
            actions.append("dropped review_item.triage_note")
    eng.dispose()
    return actions


def _query_loop(engine: str, sql: str, params: dict, stop: threading.Event,
                samples: list[float], errors: list[str], port: int | None = None) -> None:
    # API style reads take no transaction of their own. A reader that leaves a
    # transaction open holds a table lock and blocks DDL, and on MariaDB it also
    # pins an old read view for the whole run.
    eng = make_engine(engine, role="cp_api", port=port, pool_pre_ping=False,
                      isolation_level="AUTOCOMMIT")
    try:
        with eng.connect() as conn:
            while not stop.is_set():
                start = time.perf_counter()
                try:
                    conn.execute(sa.text(sql), params).fetchall()
                    samples.append((time.perf_counter() - start) * 1000)
                except Exception as exc:  # noqa: BLE001 - recorded, not raised
                    errors.append(f"{type(exc).__name__}: {exc}"[:300])
                    break
                time.sleep(0.01)
    finally:
        eng.dispose()


def _insert_loop(engine: str, stop: threading.Event, committed: list[int],
                 errors: list[str], port: int | None = None, scale: int = 1) -> None:
    """Append observations while the migration runs, to see writer blocking."""

    from .workload import insert_observation_batch, next_sequence

    eng = make_engine(engine, role="cp_worker", port=port)
    seq_start = next_sequence(eng, 90)
    counter = 0
    try:
        while not stop.is_set():
            try:
                counter += insert_observation_batch(
                    eng, engine, tag="migration", batch=20, offset=counter,
                    seq_start=seq_start, artifact_root=config.ARTIFACT_DIR / f"scale{scale}")
                committed.append(counter)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{type(exc).__name__}: {exc}"[:300])
                break
            time.sleep(0.05)
    finally:
        eng.dispose()


def compat_migration(engine: str, scale: int, port: int | None = None) -> dict:
    """Run the backward compatible migration while old queries keep running."""

    old_sql = (
        "SELECT id, amount_minor, observed_at FROM price_observation "
        "WHERE card_identity_id = :card ORDER BY observed_at DESC LIMIT 20"
    )
    from .generate import card_uuid

    params = {"card": card_uuid(7)}
    stop = threading.Event()
    samples: list[float] = []
    errors: list[str] = []
    written: list[int] = []
    reader = threading.Thread(target=_query_loop,
                              args=(engine, old_sql, params, stop, samples, errors, port))
    writer = threading.Thread(target=_insert_loop,
                              args=(engine, stop, written, errors, port, scale))
    reader.start()
    writer.start()
    time.sleep(1.0)
    outcome = run_alembic(engine, ["upgrade", "0002"], port, lock_timeout_seconds=120)
    time.sleep(0.5)
    stop.set()
    reader.join(timeout=30)
    writer.join(timeout=30)

    new_sql = (
        "SELECT id, amount_minor, freshness_note FROM price_observation "
        "WHERE card_identity_id = :card ORDER BY observed_at DESC LIMIT 20"
    )
    eng = make_engine(engine, role="cp_api", port=port)
    with eng.connect() as conn:
        new_rows = len(conn.execute(sa.text(new_sql), params).fetchall())
    eng.dispose()
    return {
        "migration": outcome,
        "old_query_samples": len(samples),
        "old_query_max_ms": max(samples) if samples else None,
        "old_query_p95_ms": percentile(samples, 0.95) if samples else None,
        "old_query_errors": errors,
        "writer_batches": written[-1] if written else 0,
        "new_query_rows": new_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["postgres", "mariadb"])
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--step", required=True,
                        choices=["initial", "offline", "compat", "failing", "downgrade"])
    args = parser.parse_args()

    match args.step:
        case "initial":
            outcome = run_alembic(args.engine, ["upgrade", "0001"], args.port)
            data = {"upgrade": outcome, "revision": current_revision(args.engine, args.port)}
        case "offline":
            target = config.RESULT_DIR / args.engine / "common"
            target.mkdir(parents=True, exist_ok=True)
            sql_path = target / "offline-upgrade-head.sql"
            outcome = run_alembic(args.engine, ["upgrade", "head", "--sql"], args.port,
                                  stdout_path=sql_path)
            data = {
                "offline": outcome,
                "sql_path": str(sql_path),
                "sql_bytes": sql_path.stat().st_size,
                "statements": sql_path.read_text().count(";"),
            }
        case "compat":
            data = compat_migration(args.engine, args.scale, args.port)
            data["revision"] = current_revision(args.engine, args.port)
        case "downgrade":
            # The boundary between rolling a change back and restoring a backup:
            # a backward compatible change can be reversed with downgrade.
            down = run_alembic(args.engine, ["downgrade", "0001"], args.port,
                               lock_timeout_seconds=120)
            revision_after_downgrade = current_revision(args.engine, args.port)
            columns_after_downgrade = [
                c["name"] for c in sa.inspect(make_engine(args.engine, port=args.port))
                .get_columns("price_observation")
            ]
            up = run_alembic(args.engine, ["upgrade", "0002"], args.port,
                             lock_timeout_seconds=120)
            data = {
                "downgrade": down,
                "revision_after_downgrade": revision_after_downgrade,
                "freshness_note_after_downgrade": "freshness_note" in columns_after_downgrade,
                "reupgrade": up,
                "revision_after_reupgrade": current_revision(args.engine, args.port),
            }
        case "failing":
            before = current_revision(args.engine, args.port)
            with timer() as elapsed:
                outcome = run_alembic(args.engine, ["upgrade", "0003"], args.port)
            after = current_revision(args.engine, args.port)
            state = object_state(args.engine, args.port)
            partial = any(state.values())
            repairs = repair_partial(args.engine, args.port) if partial else []
            data = {
                "upgrade": outcome,
                "seconds": elapsed["seconds"],
                "revision_before": before,
                "revision_after": after,
                "objects_after_failure": state,
                "partially_applied": partial,
                "repair_actions": repairs,
                "objects_after_repair": object_state(args.engine, args.port),
            }

    result = Result(step=f"migrate-{args.step}", engine=args.engine,
                    scale=args.scale if args.step in {"compat"} else None, data=data)
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str)[:3000])
    print(f"wrote {result.write()}")
    if args.step != "failing":
        outcome = (data.get("upgrade") or data.get("offline") or data.get("migration")
                   or data.get("downgrade") or {})
        if outcome.get("returncode") or data.get("reupgrade", {}).get("returncode"):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
