"""Concurrent query benchmark: 8 readers and 2 writers, per the DB requirements."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from datetime import UTC, datetime

import sqlalchemy as sa

from . import config, queries
from .util import Result, make_engine, summarize, timer
from .workload import build_batch, next_sequence, write_batch

QUERY_NAMES = tuple(queries.QUERIES)


def _reader(engine_name: str, reader_id: int, seconds: float, cards: int, observations: int,
            port: int | None, out: mp.Queue) -> None:
    # Single statement reads run in autocommit, as an API would. Holding a
    # transaction open across the run would freeze the snapshot and block DDL.
    eng = make_engine(engine_name, role="cp_api", port=port, isolation_level="AUTOCOMMIT")
    samples: dict[str, list[float]] = {name: [] for name in QUERY_NAMES}
    errors: list[str] = []
    deadline = time.perf_counter() + seconds
    iteration = reader_id * 100_000
    try:
        with eng.connect() as conn:
            while time.perf_counter() < deadline:
                name = QUERY_NAMES[iteration % len(QUERY_NAMES)]
                params = queries.params_for(name, iteration, cards, observations)
                start = time.perf_counter()
                try:
                    conn.execute(queries.statement(name, engine_name), params).fetchall()
                except Exception as exc:  # noqa: BLE001 - recorded as a failure sample
                    errors.append(f"{name}: {type(exc).__name__}: {exc}"[:300])
                    conn.rollback()
                else:
                    samples[name].append((time.perf_counter() - start) * 1000)
                iteration += 1
    finally:
        eng.dispose()
    out.put({"kind": "reader", "id": reader_id, "samples": samples, "errors": errors})


def _writer(engine_name: str, writer_id: int, seconds: float, cards: int, rows: int,
            port: int | None, out: mp.Queue, artifact_root=None) -> None:
    eng = make_engine(engine_name, role="cp_worker", port=port)
    latencies: list[float] = []
    errors: list[str] = []
    written = 0
    seq = next_sequence(eng, writer_id)
    deadline = time.perf_counter() + seconds
    try:
        while time.perf_counter() < deadline:
            seq += 1
            batch = build_batch(writer_id, seq, rows, cards, tag="bench",
                                artifact_root=artifact_root)
            start = time.perf_counter()
            try:
                with eng.begin() as conn:
                    counts = write_batch(conn, engine_name, batch)
                written += counts["price_observation"]
                latencies.append((time.perf_counter() - start) * 1000)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{type(exc).__name__}: {exc}"[:300])
    finally:
        eng.dispose()
    out.put({"kind": "writer", "id": writer_id, "latencies": latencies, "written": written,
             "errors": errors})


def _server_counters(engine_name: str, port: int | None) -> dict:
    eng = make_engine(engine_name, port=port)
    out: dict = {}
    with eng.connect() as conn:
        if engine_name == "postgres":
            row = conn.execute(sa.text(
                "SELECT numbackends, xact_commit, xact_rollback, deadlocks, blks_read, blks_hit,"
                " temp_files FROM pg_stat_database WHERE datname = current_database()"
            )).mappings().one()
            out.update({k: int(v) for k, v in row.items()})
            out["max_connections"] = int(conn.execute(
                sa.text("SELECT setting::int FROM pg_settings WHERE name = 'max_connections'")
            ).scalar_one())
            out["active_connections"] = int(conn.execute(
                sa.text("SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database()")
            ).scalar_one())
        else:
            for var in ("Threads_connected", "Innodb_deadlocks", "Innodb_row_lock_waits",
                        "Innodb_row_lock_time_max", "Innodb_buffer_pool_reads",
                        "Innodb_buffer_pool_read_requests", "Slow_queries"):
                value = conn.execute(sa.text(f"SHOW GLOBAL STATUS LIKE '{var}'")).fetchone()
                out[var] = int(value[1]) if value else None
            out["max_connections"] = int(conn.execute(
                sa.text("SELECT @@GLOBAL.max_connections")).scalar_one())
    eng.dispose()
    return out


def _server_statements(engine_name: str, port: int | None) -> list[dict]:
    """Server-side timings, so the result does not depend on client overhead."""

    eng = make_engine(engine_name, port=port)
    rows: list[dict] = []
    with eng.connect() as conn:
        if engine_name == "postgres":
            try:
                conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
                conn.commit()
                result = conn.execute(sa.text(
                    "SELECT calls, round(mean_exec_time::numeric, 3) AS mean_ms,"
                    " round(max_exec_time::numeric, 3) AS max_ms, left(query, 120) AS query"
                    " FROM pg_stat_statements ORDER BY calls DESC LIMIT 12"
                )).mappings().all()
                rows = [dict(r) for r in result]
            except sa.exc.DatabaseError as exc:
                rows = [{"error": str(exc)[:200]}]
        else:
            result = conn.execute(sa.text(
                "SELECT COUNT_STAR AS calls,"
                " ROUND(AVG_TIMER_WAIT/1000000000, 3) AS mean_ms,"
                " ROUND(MAX_TIMER_WAIT/1000000000, 3) AS max_ms,"
                " LEFT(DIGEST_TEXT, 120) AS query"
                " FROM performance_schema.events_statements_summary_by_digest"
                " WHERE SCHEMA_NAME = :schema ORDER BY COUNT_STAR DESC LIMIT 12"
            ), {"schema": config.DB_NAME}).mappings().all()
            rows = [dict(r) for r in result]
    eng.dispose()
    return rows


def _reset_statement_stats(engine_name: str, port: int | None) -> None:
    eng = make_engine(engine_name, port=port, isolation_level="AUTOCOMMIT")
    with eng.connect() as conn:
        if engine_name == "postgres":
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
            conn.exec_driver_sql("SELECT pg_stat_statements_reset()")
            conn.exec_driver_sql("SELECT pg_stat_reset()")
        else:
            conn.exec_driver_sql("TRUNCATE performance_schema.events_statements_summary_by_digest")
            conn.exec_driver_sql("FLUSH STATUS")
    eng.dispose()


def measure_single(engine_name: str, cards: int, observations: int, port: int | None,
                   iterations: int = 1) -> dict[str, list[float]]:
    """Run each query without competing load (cold or warm depending on caller)."""

    eng = make_engine(engine_name, role="cp_api", port=port, isolation_level="AUTOCOMMIT")
    samples: dict[str, list[float]] = {}
    with eng.connect() as conn:
        for name in QUERY_NAMES:
            values = []
            for i in range(iterations):
                params = queries.params_for(name, i + 1, cards, observations)
                start = time.perf_counter()
                conn.execute(queries.statement(name, engine_name), params).fetchall()
                values.append((time.perf_counter() - start) * 1000)
            samples[name] = values
    eng.dispose()
    return samples


def plans(engine_name: str, cards: int, observations: int, port: int | None) -> dict[str, str]:
    eng = make_engine(engine_name, role="cp_admin", port=port)
    out: dict[str, str] = {}
    prefix = ("EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) " if engine_name == "postgres"
              else "EXPLAIN FORMAT=JSON ")
    with eng.connect() as conn:
        for name in QUERY_NAMES:
            params = queries.params_for(name, 3, cards, observations)
            explain = sa.text(prefix + queries.QUERIES[name][engine_name])
            expanding = queries.EXPANDING.get(name)
            if expanding:
                explain = explain.bindparams(sa.bindparam(expanding, expanding=True))
            try:
                rows = conn.execute(explain, params).fetchall()
                out[name] = "\n".join(str(r[0]) for r in rows)
            except Exception as exc:  # noqa: BLE001
                out[name] = f"EXPLAIN failed: {type(exc).__name__}: {exc}"[:500]
                conn.rollback()
    eng.dispose()
    return out


def run(engine_name: str, scale: int, seconds: float, readers: int, writers: int,
        rows_per_batch: int, port: int | None) -> dict:
    profile = config.PROFILES[scale]
    cards = profile.cards
    observations = profile.price_observation

    warm = measure_single(engine_name, cards, observations, port, iterations=3)
    _reset_statement_stats(engine_name, port)
    before = _server_counters(engine_name, port)

    queue: mp.Queue = mp.Queue()
    processes = []
    for i in range(readers):
        processes.append(mp.Process(target=_reader, args=(
            engine_name, i + 1, seconds, cards, observations, port, queue)))
    for i in range(writers):
        processes.append(mp.Process(target=_writer, args=(
            engine_name, 10 + i, seconds, cards, rows_per_batch, port, queue,
            config.ARTIFACT_DIR / f"scale{scale}")))

    peak_connections = 0
    with timer() as elapsed:
        for process in processes:
            process.start()
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            time.sleep(2.0)
            try:
                counters = _server_counters(engine_name, port)
                current = counters.get("active_connections") or counters.get("Threads_connected") or 0
                peak_connections = max(peak_connections, int(current))
            except Exception:  # noqa: BLE001 - sampling must not fail the run
                pass
        results = [queue.get() for _ in processes]
        for process in processes:
            process.join(timeout=60)

    after = _server_counters(engine_name, port)
    reader_samples: dict[str, list[float]] = {name: [] for name in QUERY_NAMES}
    errors: list[str] = []
    writer_latencies: list[float] = []
    written = 0
    for item in results:
        if item["kind"] == "reader":
            for name, values in item["samples"].items():
                reader_samples[name].extend(values)
            errors.extend(item["errors"])
        else:
            writer_latencies.extend(item["latencies"])
            written += item["written"]
            errors.extend(item["errors"])

    summary = {name: summarize(values) for name, values in reader_samples.items()}
    verdict = {
        name: {
            "target_p95_ms": queries.TARGET_P95_MS[name],
            "p95_ms": summary[name].get("p95_ms"),
            "pass": bool(summary[name].get("count")) and
                    summary[name]["p95_ms"] <= queries.TARGET_P95_MS[name],
        }
        for name in QUERY_NAMES
    }
    return {
        "duration_seconds": elapsed["seconds"],
        "readers": readers,
        "writers": writers,
        "rows_per_write_batch": rows_per_batch,
        "warm_single_ms": warm,
        "concurrent": summary,
        "verdict": verdict,
        "writer_batch_ms": summarize(writer_latencies),
        "observations_written": written,
        "errors": errors[:20],
        "error_count": len(errors),
        "counters_before": before,
        "counters_after": after,
        "peak_connections": peak_connections,
        "server_statements": _server_statements(engine_name, port),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["postgres", "mariadb"])
    parser.add_argument("--scale", type=int, choices=[1, 10], required=True)
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--readers", type=int, default=8)
    parser.add_argument("--writers", type=int, default=2)
    parser.add_argument("--rows-per-batch", type=int, default=60)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--cold", action="store_true",
                        help="measure one pass per query without warming first")
    args = parser.parse_args()

    profile = config.PROFILES[args.scale]
    if args.cold:
        samples = measure_single(args.engine, profile.cards, profile.price_observation,
                                 args.port, iterations=1)
        data = {"cold_single_ms": samples}
        result = Result(step="bench-cold", engine=args.engine, scale=args.scale, data=data)
    else:
        data = run(args.engine, args.scale, args.seconds, args.readers, args.writers,
                   args.rows_per_batch, args.port)
        data["plans"] = plans(args.engine, profile.cards, profile.price_observation, args.port)
        result = Result(step="bench", engine=args.engine, scale=args.scale, data=data)
    print(json.dumps({k: v for k, v in data.items() if k not in {"plans", "server_statements"}},
                     indent=2, default=str)[:4000])
    print(f"wrote {result.write()}")


if __name__ == "__main__":
    main()
