"""Runtime ingestion throughput: one normal day and a full 28-day reparse.

DB-CAP-04 requires committing a normal day's 30,000 extracted rows and derived
rows within 10 minutes while reads continue, and appending the equivalent of a
28-day reparse within 8 hours. Both run with every constraint enforced.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa

from . import config, queries
from .generate import RECORDS_PER_RUN, card_uuid, observation_fields
from .util import Result, make_engine, summarize, timer
from .workload import (ID_BASE, INSERTS, WRITER_STRIDE, build_batch, insert_observations,
                       next_sequence, write_batch)

DAILY_WRITER = 40
REPARSE_WRITER = 41


def _reader_loop(engine_name: str, port: int | None, stop: Any, out: mp.Queue,
                 scale: int) -> None:
    profile = config.PROFILES[scale]
    eng = make_engine(engine_name, role="cp_api", port=port, isolation_level="AUTOCOMMIT")
    samples: list[float] = []
    iteration = 0
    try:
        with eng.connect() as conn:
            while not stop.is_set():
                iteration += 1
                name = "DB-QRY-01" if iteration % 2 else "DB-QRY-05"
                params = queries.params_for(name, iteration, profile.cards,
                                            profile.price_observation)
                start = time.perf_counter()
                conn.execute(queries.statement(name, engine_name), params).fetchall()
                samples.append((time.perf_counter() - start) * 1000)
                time.sleep(0.05)
    finally:
        eng.dispose()
    out.put(samples)


def daily_ingest(engine_name: str, scale: int, port: int | None) -> dict:
    """Append one normal day while API-style reads continue."""

    profile = config.PROFILES[scale]
    artifacts = 500 * scale
    eng = make_engine(engine_name, role="cp_worker", port=port)
    seq_start = next_sequence(eng, DAILY_WRITER)
    artifact_root = config.ARTIFACT_DIR / f"scale{scale}"
    observed = datetime.now(UTC).replace(tzinfo=None)

    stop = mp.Event()
    queue: mp.Queue = mp.Queue()
    reader = mp.Process(target=_reader_loop, args=(engine_name, port, stop, queue, scale))
    reader.start()

    batch_times: list[float] = []
    rows_written = 0
    with timer() as elapsed:
        for index in range(artifacts):
            batch = build_batch(DAILY_WRITER, seq_start + index + 1, RECORDS_PER_RUN,
                                profile.cards, observed_at=observed, tag="daily",
                                artifact_root=artifact_root)
            start = time.perf_counter()
            with eng.begin() as conn:
                counts = write_batch(conn, engine_name, batch)
            batch_times.append((time.perf_counter() - start) * 1000)
            rows_written += sum(counts.values())
    eng.dispose()

    stop.set()
    read_samples = queue.get(timeout=60)
    reader.join(timeout=30)

    return {
        "artifacts": artifacts,
        "extracted_rows": artifacts * RECORDS_PER_RUN,
        "total_rows_written": rows_written,
        "seconds": elapsed["seconds"],
        "rows_per_second": rows_written / elapsed["seconds"],
        "batch_commit_ms": summarize(batch_times),
        "concurrent_read_ms": summarize(read_samples),
        "limit_seconds": 600,
        "pass": elapsed["seconds"] <= 600,
    }


def _reparse_batch(scale: int, artifact_index: int, cards: int, writer_id: int,
                   seq: int, now: datetime) -> dict[str, list[dict]]:
    """Rebuild one stored artifact's rows, including its original observation keys."""

    profile = config.PROFILES[scale]
    artifact_id = artifact_index + 1
    processing_id = ID_BASE["processing_run"] + writer_id * WRITER_STRIDE + seq
    records, candidates, attempts, observations = [], [], [], []
    for row in range(RECORDS_PER_RUN):
        i = artifact_index * RECORDS_PER_RUN + row
        fields = observation_fields(i, scale)
        counter = seq * RECORDS_PER_RUN + row
        record_id = ID_BASE["extracted_record"] + writer_id * WRITER_STRIDE + counter
        candidate_id = ID_BASE["observation_candidate"] + writer_id * WRITER_STRIDE + counter
        observation_id = ID_BASE["price_observation"] + writer_id * WRITER_STRIDE + counter
        card = card_uuid(fields["card_index"])
        records.append({
            "id": record_id, "processing_run_id": processing_id, "raw_artifact_id": artifact_id,
            "locator": f"$.items[{row}]",
            "payload": '{"reparse":true,"row":%d,"price":%d}' % (row, fields["amount"]),
            "value_origin": "artifact", "confidence": 0.99, "created_at": now,
        })
        candidates.append({
            "id": candidate_id, "extracted_record_id": record_id,
            "shop_id": fields["source_id"], "source_id": fields["source_id"], "tcg": config.TCG,
            "amount_minor": fields["amount"], "currency": config.CURRENCY,
            "price_type": fields["price_type"], "raw_card_name": f"card{fields['card_index']}",
            "raw_card_number": f"{fields['card_index'] % 1000:03d}/165",
            "raw_set": f"SV{fields['card_index'] // 1000:03d}", "raw_rarity": "RR",
            "raw_edition": "1st", "raw_language": "ja", "raw_condition": fields["condition"],
            "observed_at": fields["observed"].replace(tzinfo=None),
            "promotion_rule_version": "v2", "created_at": now,
        })
        attempts.append({
            "id": ID_BASE["identity_resolution_attempt"] + writer_id * WRITER_STRIDE + counter * 2,
            "observation_candidate_id": candidate_id, "matcher_name": "attribute_matcher",
            "matcher_version": "1.1.0", "card_identity_id": card, "match_score": 0.99,
            "result": "confirmed", "evidence": "set+number+rarity", "created_at": now,
        })
        observations.append({
            "id": observation_id, "observation_candidate_id": candidate_id,
            "card_identity_id": card, "shop_id": fields["source_id"],
            "source_id": fields["source_id"], "raw_artifact_id": artifact_id,
            "tcg": config.TCG, "amount_minor": fields["amount"], "currency": config.CURRENCY,
            "price_type": fields["price_type"], "card_condition": fields["condition"],
            "observed_at": fields["observed"].replace(tzinfo=None),
            "collected_at": fields["observed"].replace(tzinfo=None),
            "idempotency_key": fields["idempotency_key"], "created_at": now,
        })
    return {
        "ingest_run": [], "raw_artifact": [], "review_item": [],
        "processing_run": [{
            "id": processing_id, "raw_artifact_id": artifact_id,
            "processor_name": "price_table_parser", "processor_version": "1.1.0",
            "config_ref": "config/v2", "attempt_no": 2, "started_at": now,
            "finished_at": now, "extracted_count": RECORDS_PER_RUN,
            "promoted_count": RECORDS_PER_RUN,
        }],
        "extracted_record": records, "observation_candidate": candidates,
        "identity_resolution_attempt": attempts, "price_observation": observations,
    }


def reparse(engine_name: str, scale: int, port: int | None, artifacts: int | None = None) -> dict:
    """Reprocess stored artifacts; the same observations must not duplicate."""

    profile = config.PROFILES[scale]
    total_artifacts = 500 * scale * profile.days
    target = artifacts or total_artifacts
    eng = make_engine(engine_name, role="cp_worker", port=port)
    seq_start = next_sequence(eng, REPARSE_WRITER)
    now = datetime.now(UTC).replace(tzinfo=None)

    with eng.connect() as conn:
        before = int(conn.execute(sa.text("SELECT COUNT(*) FROM price_observation")).scalar_one())

    inserted_observations = 0
    batch_times: list[float] = []
    with timer() as elapsed:
        for index in range(target):
            batch = _reparse_batch(scale, index, profile.cards, REPARSE_WRITER,
                                   seq_start + index + 1, now)
            start = time.perf_counter()
            with eng.begin() as conn:
                for table in ("processing_run", "extracted_record", "observation_candidate",
                              "identity_resolution_attempt"):
                    rows = batch[table]
                    if rows:
                        conn.execute(sa.text(INSERTS[table]), rows)
                inserted_observations += insert_observations(
                    conn, engine_name, batch["price_observation"], idempotent=True)
            batch_times.append((time.perf_counter() - start) * 1000)

    with eng.connect() as conn:
        after = int(conn.execute(sa.text("SELECT COUNT(*) FROM price_observation")).scalar_one())
        duplicate_keys = int(conn.execute(sa.text(
            "SELECT COUNT(*) FROM (SELECT idempotency_key FROM price_observation"
            " GROUP BY idempotency_key HAVING COUNT(*) > 1) d")).scalar_one())
    eng.dispose()

    rows_per_artifact = 1 + RECORDS_PER_RUN * 3  # run, records, candidates, attempts
    appended = target * rows_per_artifact
    seconds_full = elapsed["seconds"] * (total_artifacts / target)
    return {
        "artifacts_reparsed": target,
        "artifacts_in_profile": total_artifacts,
        "sampled": target < total_artifacts,
        "appended_rows": appended,
        "seconds": elapsed["seconds"],
        "rows_per_second": appended / elapsed["seconds"],
        "projected_full_reparse_seconds": seconds_full,
        "limit_seconds": 8 * 3600,
        "observations_before": before,
        "observations_after": after,
        "new_observations": after - before,
        "duplicate_idempotency_keys": duplicate_keys,
        "batch_commit_ms": summarize(batch_times),
        "pass": duplicate_keys == 0 and after == before and seconds_full <= 8 * 3600,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["postgres", "mariadb"])
    parser.add_argument("--scale", type=int, choices=[1, 10], required=True)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--step", choices=["daily", "reparse"], required=True)
    parser.add_argument("--artifacts", type=int, default=None,
                        help="reparse only this many artifacts and extrapolate")
    args = parser.parse_args()

    if args.step == "daily":
        data = daily_ingest(args.engine, args.scale, args.port)
    else:
        data = reparse(args.engine, args.scale, args.port, args.artifacts)
    result = Result(step=f"ingest-{args.step}", engine=args.engine, scale=args.scale, data=data)
    print(json.dumps(data, indent=2, default=str)[:2500])
    print(f"wrote {result.write()}")


if __name__ == "__main__":
    main()
