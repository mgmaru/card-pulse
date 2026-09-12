"""Integrity, idempotency, isolation, and contention checks (DB-INT-01..08).

Every check reports what the database did, so a failure is recorded as evidence
rather than raised.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa

from . import config
from .generate import card_uuid
from .util import Result, make_engine
from .workload import (ID_BASE, WRITER_STRIDE, build_batch, insert_observations, next_sequence,
                       observation_insert, write_batch)

PROBE_WRITER = 70
CONFLICT_WRITER = 71
# Probe rows are appended, never deleted, so each run needs its own identifier
# window inside the writer range.
RUN_OFFSET = int(time.time()) % 100_000 * 10_000


def _error_signature(exc: Exception) -> dict[str, Any]:
    """What an application can branch on when a statement fails."""

    orig = getattr(exc, "orig", exc)
    signature: dict[str, Any] = {
        "sqlalchemy_class": type(exc).__name__,
        "driver_class": type(orig).__name__,
        "message": str(orig)[:200],
    }
    sqlstate = getattr(orig, "sqlstate", None)
    if sqlstate is None:
        diag = getattr(orig, "diag", None)
        sqlstate = getattr(diag, "sqlstate", None) if diag else None
    signature["sqlstate"] = sqlstate
    args = getattr(orig, "args", ())
    if args and isinstance(args[0], int):
        signature["errno"] = args[0]
    constraint = None
    diag = getattr(orig, "diag", None)
    if diag is not None:
        constraint = getattr(diag, "constraint_name", None)
    signature["constraint"] = constraint
    return signature


def _observation_row(engine_name: str, eng: sa.Engine, key: str | None = None,
                     observation_id: int | None = None, **overrides: Any) -> dict:
    batch = build_batch(PROBE_WRITER, 1, 1, config.PROFILES[1].cards, tag="probe")
    row = dict(batch["price_observation"][0])
    with eng.connect() as conn:
        candidate_id = conn.execute(sa.text(
            "SELECT id FROM observation_candidate ORDER BY id LIMIT 1")).scalar_one()
        artifact_id = conn.execute(sa.text(
            "SELECT id FROM raw_artifact ORDER BY id LIMIT 1")).scalar_one()
    row["observation_candidate_id"] = candidate_id
    row["raw_artifact_id"] = artifact_id
    if key is not None:
        row["idempotency_key"] = key
    if observation_id is not None:
        row["id"] = observation_id
    row.update(overrides)
    return row


def _count_key(eng: sa.Engine, key: str) -> int:
    with eng.connect() as conn:
        return int(conn.execute(
            sa.text("SELECT COUNT(*) FROM price_observation WHERE idempotency_key = :k"),
            {"k": key}).scalar_one())


def check_idempotent_sequential(engine_name: str, port: int | None) -> dict:
    eng = make_engine(engine_name, role="cp_worker", port=port)
    key = f"poc-idem-seq-{uuid.uuid4()}"
    base_id = ID_BASE["price_observation"] + PROBE_WRITER * WRITER_STRIDE + RUN_OFFSET
    first = _observation_row(engine_name, eng, key=key, observation_id=base_id + 1)
    second = _observation_row(engine_name, eng, key=key, observation_id=base_id + 2,
                              amount_minor=first["amount_minor"] + 10)
    with eng.begin() as conn:
        insert_observations(conn, engine_name, [first])
    with eng.begin() as conn:
        insert_observations(conn, engine_name, [second])
    strict_error = None
    try:
        with eng.begin() as conn:
            conn.execute(sa.text(observation_insert(engine_name, idempotent=False)), second)
    except sa.exc.IntegrityError as exc:
        strict_error = _error_signature(exc)
    stored = _count_key(eng, key)
    eng.dispose()
    return {
        "idempotency_key": key,
        "rows_after_two_inserts": stored,
        "expected_rows": 1,
        "pass": stored == 1 and strict_error is not None,
        "strict_insert_error": strict_error,
    }


def _concurrent_worker(engine_name: str, port: int | None, key: str, observation_id: int,
                       barrier: Any, out: mp.Queue) -> None:
    eng = make_engine(engine_name, role="cp_worker", port=port)
    row = _observation_row(engine_name, eng, key=key, observation_id=observation_id)
    barrier.wait(timeout=30)
    outcome: dict[str, Any] = {"observation_id": observation_id}
    try:
        with eng.begin() as conn:
            outcome["rowcount"] = insert_observations(conn, engine_name, [row])
    except Exception as exc:  # noqa: BLE001
        outcome["error"] = _error_signature(exc)
    finally:
        eng.dispose()
    out.put(outcome)


def check_idempotent_concurrent(engine_name: str, port: int | None, writers: int = 2) -> dict:
    key = f"poc-idem-conc-{uuid.uuid4()}"
    base_id = ID_BASE["price_observation"] + CONFLICT_WRITER * WRITER_STRIDE + RUN_OFFSET
    barrier = mp.Barrier(writers)
    queue: mp.Queue = mp.Queue()
    processes = [
        mp.Process(target=_concurrent_worker,
                   args=(engine_name, port, key, base_id + i + 1, barrier, queue))
        for i in range(writers)
    ]
    for process in processes:
        process.start()
    outcomes = [queue.get(timeout=60) for _ in processes]
    for process in processes:
        process.join(timeout=30)
    eng = make_engine(engine_name, port=port)
    stored = _count_key(eng, key)
    eng.dispose()
    return {
        "idempotency_key": key,
        "writers": writers,
        "rows_after_concurrent_insert": stored,
        "expected_rows": 1,
        "pass": stored == 1,
        "outcomes": outcomes,
    }


def check_constraints(engine_name: str, port: int | None) -> dict:
    """Reject invalid observations and leave nothing behind from the same transaction."""

    eng = make_engine(engine_name, role="cp_worker", port=port)
    base_id = ID_BASE["price_observation"] + PROBE_WRITER * WRITER_STRIDE + RUN_OFFSET + 100
    existing_key = None
    with eng.connect() as conn:
        existing_key = conn.execute(sa.text(
            "SELECT idempotency_key FROM price_observation ORDER BY id LIMIT 1")).scalar_one()

    cases = {
        "not_null_currency": {"currency": None},
        "check_negative_amount": {"amount_minor": -1},
        "check_price_type": {"price_type": "auction"},
        "foreign_key_card": {"card_identity_id": str(uuid.uuid4())},
        "unique_idempotency_key": {"idempotency_key": existing_key},
    }
    results: dict[str, Any] = {}
    statement = sa.text(observation_insert(engine_name, idempotent=False))
    for index, (name, override) in enumerate(cases.items()):
        canary_key = f"poc-canary-{name}-{uuid.uuid4()}"
        canary = _observation_row(engine_name, eng, key=canary_key,
                                  observation_id=base_id + index * 10 + 1)
        bad = _observation_row(engine_name, eng, key=f"poc-bad-{name}-{uuid.uuid4()}",
                               observation_id=base_id + index * 10 + 2, **override)
        signature = None
        try:
            with eng.begin() as conn:
                conn.execute(statement, canary)  # committed only if the batch succeeds
                conn.execute(statement, bad)
        except sa.exc.DatabaseError as exc:
            signature = _error_signature(exc)
        canary_rows = _count_key(eng, canary_key)
        results[name] = {
            "rejected": signature is not None,
            "error": signature,
            "canary_rows_after_rollback": canary_rows,
            "pass": signature is not None and canary_rows == 0,
        }

    zero_key = f"poc-zero-{uuid.uuid4()}"
    zero_row = _observation_row(engine_name, eng, key=zero_key, observation_id=base_id + 900,
                                amount_minor=0)
    with eng.begin() as conn:
        conn.execute(statement, zero_row)
    results["zero_price_accepted"] = {
        "rows": _count_key(eng, zero_key),
        "pass": _count_key(eng, zero_key) == 1,
    }
    eng.dispose()
    return {"cases": results, "pass": all(case["pass"] for case in results.values())}


def check_as_of_snapshot(engine_name: str, port: int | None, scale: int = 1) -> dict:
    """One API response must read a single consistent snapshot (DB-INT-04)."""

    reader = make_engine(engine_name, role="cp_api", port=port)
    writer = make_engine(engine_name, role="cp_worker", port=port)
    seq = next_sequence(writer, PROBE_WRITER) + 1
    count_sql = sa.text("SELECT COUNT(*) FROM price_observation")
    max_sql = sa.text("SELECT COALESCE(MAX(collected_at), :epoch) FROM price_observation")
    epoch = datetime(2000, 1, 1)
    with reader.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
        conn.begin()
        first_count = int(conn.execute(count_sql).scalar_one())
        first_max = conn.execute(max_sql, {"epoch": epoch}).scalar_one()
        batch = build_batch(PROBE_WRITER, seq, 5, config.PROFILES[1].cards, tag="snapshot",
                            artifact_root=config.ARTIFACT_DIR / f"scale{scale}")
        with writer.begin() as wconn:
            write_batch(wconn, engine_name, batch)
        time.sleep(0.2)
        second_count = int(conn.execute(count_sql).scalar_one())
        second_max = conn.execute(max_sql, {"epoch": epoch}).scalar_one()
        conn.rollback()
    with reader.connect() as conn:
        after_count = int(conn.execute(count_sql).scalar_one())
    reader.dispose()
    writer.dispose()
    return {
        "isolation_level": "REPEATABLE READ",
        "count_at_first_read": first_count,
        "count_at_second_read": second_count,
        "count_after_transaction": after_count,
        "snapshot_stable": first_count == second_count and first_max == second_max,
        "writer_committed_during_read": after_count > second_count,
        "pass": first_count == second_count and after_count > second_count,
    }


def _review_decider(engine_name: str, port: int | None, review_id: int, who: str,
                    barrier: Any, out: mp.Queue) -> None:
    eng = make_engine(engine_name, role="cp_worker", port=port)
    outcome: dict[str, Any] = {"actor": who}
    try:
        with eng.begin() as conn:
            version = conn.execute(sa.text(
                "SELECT lock_version FROM review_item WHERE id = :id"), {"id": review_id}
            ).scalar_one()
            barrier.wait(timeout=30)
            result = conn.execute(sa.text(
                "UPDATE review_item SET state = 'decided', decided_at = :now, decided_by = :who,"
                " decision = 'confirmed', lock_version = lock_version + 1"
                " WHERE id = :id AND state = 'pending' AND lock_version = :version"),
                {"id": review_id, "who": who, "now": datetime.now(UTC).replace(tzinfo=None),
                 "version": version})
            outcome["rowcount"] = result.rowcount
    except Exception as exc:  # noqa: BLE001
        outcome["error"] = _error_signature(exc)
    finally:
        eng.dispose()
    out.put(outcome)


def check_review_contention(engine_name: str, port: int | None) -> dict:
    eng = make_engine(engine_name, port=port)
    with eng.connect() as conn:
        review_id = conn.execute(sa.text(
            "SELECT id FROM review_item WHERE state = 'pending' ORDER BY id LIMIT 1")).scalar_one()
    barrier = mp.Barrier(2)
    queue: mp.Queue = mp.Queue()
    processes = [
        mp.Process(target=_review_decider,
                   args=(engine_name, port, review_id, who, barrier, queue))
        for who in ("owner-session-a", "owner-session-b")
    ]
    for process in processes:
        process.start()
    outcomes = [queue.get(timeout=60) for _ in processes]
    for process in processes:
        process.join(timeout=30)
    with eng.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT state, decided_by, lock_version FROM review_item WHERE id = :id"),
            {"id": review_id}).mappings().one()
    eng.dispose()
    winners = [o for o in outcomes if o.get("rowcount") == 1]
    return {
        "review_item_id": review_id,
        "outcomes": outcomes,
        "final_state": dict(row),
        "single_winner": len(winners) == 1,
        "pass": len(winners) == 1 and row["state"] == "decided" and row["lock_version"] == 1,
    }


def _deadlock_worker(engine_name: str, port: int | None, first: int, second: int,
                     barrier: Any, out: mp.Queue) -> None:
    eng = make_engine(engine_name, role="cp_worker", port=port)
    outcome: dict[str, Any] = {"order": [first, second]}
    update = sa.text("UPDATE review_item SET priority = priority WHERE id = :id")
    try:
        with eng.begin() as conn:
            conn.execute(update, {"id": first})
            barrier.wait(timeout=30)
            time.sleep(0.3)
            conn.execute(update, {"id": second})
        outcome["committed"] = True
    except Exception as exc:  # noqa: BLE001
        outcome["committed"] = False
        outcome["error"] = _error_signature(exc)
    finally:
        eng.dispose()
    out.put(outcome)


def check_deadlock(engine_name: str, port: int | None) -> dict:
    eng = make_engine(engine_name, port=port)
    with eng.connect() as conn:
        ids = [int(r[0]) for r in conn.execute(sa.text(
            "SELECT id FROM review_item ORDER BY id LIMIT 2")).fetchall()]
    eng.dispose()
    barrier = mp.Barrier(2)
    queue: mp.Queue = mp.Queue()
    processes = [
        mp.Process(target=_deadlock_worker,
                   args=(engine_name, port, ids[0], ids[1], barrier, queue)),
        mp.Process(target=_deadlock_worker,
                   args=(engine_name, port, ids[1], ids[0], barrier, queue)),
    ]
    for process in processes:
        process.start()
    outcomes = [queue.get(timeout=60) for _ in processes]
    for process in processes:
        process.join(timeout=30)
    failures = [o for o in outcomes if not o["committed"]]
    return {
        "outcomes": outcomes,
        "detected": len(failures) >= 1,
        "pass": len(failures) >= 1 and len(outcomes) - len(failures) >= 1,
    }


def _lock_holder(engine_name: str, port: int | None, review_id: int, hold_seconds: float,
                 ready: Any) -> None:
    eng = make_engine(engine_name, role="cp_worker", port=port)
    with eng.begin() as conn:
        conn.execute(sa.text("UPDATE review_item SET priority = priority WHERE id = :id"),
                     {"id": review_id})
        ready.set()
        time.sleep(hold_seconds)
    eng.dispose()


def check_lock_timeout(engine_name: str, port: int | None) -> dict:
    """A blocked writer must fail with a distinguishable timeout, not hang forever."""

    eng = make_engine(engine_name, port=port)
    with eng.connect() as conn:
        review_id = int(conn.execute(sa.text(
            "SELECT id FROM review_item ORDER BY id DESC LIMIT 1")).scalar_one())
    eng.dispose()
    ready = mp.Event()
    holder = mp.Process(target=_lock_holder, args=(engine_name, port, review_id, 8.0, ready))
    holder.start()
    ready.wait(timeout=30)
    waiter = make_engine(engine_name, role="cp_worker", port=port)
    signature = None
    waited = 0.0
    start = time.perf_counter()
    try:
        with waiter.begin() as conn:
            if engine_name == "postgres":
                conn.exec_driver_sql("SET LOCAL lock_timeout = '2s'")
            else:
                conn.exec_driver_sql("SET SESSION innodb_lock_wait_timeout = 2")
            conn.execute(sa.text("UPDATE review_item SET priority = priority WHERE id = :id"),
                         {"id": review_id})
    except Exception as exc:  # noqa: BLE001
        signature = _error_signature(exc)
    waited = time.perf_counter() - start
    waiter.dispose()
    holder.join(timeout=30)
    return {
        "timeout_setting": "lock_timeout=2s" if engine_name == "postgres"
                           else "innodb_lock_wait_timeout=2",
        "waited_seconds": waited,
        "error": signature,
        "pass": signature is not None and waited < 7.0,
    }


def check_type_roundtrip(engine_name: str, port: int | None) -> dict:
    """UUID, UTC timestamps, and source metadata JSON must survive the round trip."""

    eng = make_engine(engine_name, role="cp_worker", port=port)
    record_id = ID_BASE["extracted_record"] + PROBE_WRITER * WRITER_STRIDE + RUN_OFFSET + 999
    payload = {"名前": "リザードンex", "価格": "¥12,345", "nested": {"a": [1, 2, 3]},
               "unicode": "★☆♪"}
    moment = datetime(2026, 9, 11, 14, 30, 15, 123456, tzinfo=UTC)
    naive = moment.astimezone(UTC).replace(tzinfo=None)
    with eng.connect() as conn:
        run_id = conn.execute(sa.text(
            "SELECT id FROM processing_run ORDER BY id LIMIT 1")).scalar_one()
        artifact_id = conn.execute(sa.text(
            "SELECT raw_artifact_id FROM processing_run WHERE id = :id"),
            {"id": run_id}).scalar_one()
    with eng.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO extracted_record (id, processing_run_id, raw_artifact_id, locator,"
            " payload, value_origin, confidence, warnings, created_at)"
            " VALUES (:id, :run, :artifact, :locator, :payload, 'artifact', 0.9876, NULL, :ts)"),
            {"id": record_id, "run": run_id, "artifact": artifact_id, "locator": "$.roundtrip",
             "payload": json.dumps(payload, ensure_ascii=False), "ts": naive})
    with eng.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT payload, created_at, confidence FROM extracted_record WHERE id = :id"),
            {"id": record_id}).mappings().one()
        card_row = conn.execute(sa.text(
            "SELECT id FROM card_identity WHERE id = :id"), {"id": card_uuid(3)}).scalar()
    inspector = sa.inspect(eng)
    columns = {c["name"]: str(c["type"]) for c in inspector.get_columns("price_observation")}
    eng.dispose()
    stored_payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])
    stored_ts = row["created_at"]
    if stored_ts.tzinfo is not None:
        stored_ts = stored_ts.astimezone(UTC).replace(tzinfo=None)
    return {
        "json_roundtrip_equal": stored_payload == payload,
        "timestamp_roundtrip_equal": stored_ts == naive,
        "microseconds_preserved": stored_ts.microsecond == naive.microsecond,
        "uuid_lookup_matched": str(card_row) == card_uuid(3),
        "reflected_uuid_type": columns.get("card_identity_id"),
        "reflected_timestamp_type": columns.get("observed_at"),
        "pass": stored_payload == payload and stored_ts == naive
                and str(card_row) == card_uuid(3),
    }


def check_runtime_cannot_disable_checks(engine_name: str, port: int | None) -> dict:
    """Can a runtime role switch off constraint enforcement for its session?"""

    eng = make_engine(engine_name, role="cp_worker", port=port)
    statement = ("SET session_replication_role = 'replica'" if engine_name == "postgres"
                 else "SET SESSION foreign_key_checks = 0")
    signature = None
    bypassed = False
    try:
        with eng.begin() as conn:
            conn.exec_driver_sql(statement)
            row = _observation_row(engine_name, eng, key=f"poc-nofk-{uuid.uuid4()}",
                                   observation_id=ID_BASE["price_observation"]
                                   + PROBE_WRITER * WRITER_STRIDE + RUN_OFFSET + 777,
                                   card_identity_id=str(uuid.uuid4()))
            conn.execute(sa.text(observation_insert(engine_name, idempotent=False)), row)
            bypassed = True
            conn.rollback()
    except Exception as exc:  # noqa: BLE001
        signature = _error_signature(exc)
    eng.dispose()
    return {
        "statement": statement,
        "runtime_role_could_bypass_foreign_keys": bypassed,
        "error": signature,
        "pass": not bypassed,
    }


CHECKS = {
    "idempotent_sequential": check_idempotent_sequential,
    "idempotent_concurrent": check_idempotent_concurrent,
    "constraints": check_constraints,
    "as_of_snapshot": check_as_of_snapshot,
    "review_contention": check_review_contention,
    "deadlock": check_deadlock,
    "lock_timeout": check_lock_timeout,
    "type_roundtrip": check_type_roundtrip,
    "runtime_cannot_disable_checks": check_runtime_cannot_disable_checks,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["postgres", "mariadb"])
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()

    data: dict[str, Any] = {}
    for name, check in CHECKS.items():
        if args.only and name not in args.only:
            continue
        try:
            if name == "as_of_snapshot":
                data[name] = check(args.engine, args.port, args.scale)
            else:
                data[name] = check(args.engine, args.port)
        except Exception as exc:  # noqa: BLE001 - a failing check is a result
            data[name] = {"pass": False, "harness_error": f"{type(exc).__name__}: {exc}"[:400]}
        print(f"  {name}: {'pass' if data[name].get('pass') else 'see result'}", flush=True)
    data["all_passed"] = all(v.get("pass") for v in data.values() if isinstance(v, dict))
    result = Result(step="integrity", engine=args.engine, scale=args.scale, data=data)
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str)[:4000])
    print(f"wrote {result.write()}")
    broken = [name for name, value in data.items()
              if isinstance(value, dict) and value.get("harness_error")]
    if broken:
        raise SystemExit(f"harness errors in: {broken}")


if __name__ == "__main__":
    main()
