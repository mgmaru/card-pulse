"""Runtime write workload: daily ingestion, reparse, and idempotent appends.

Unlike the bulk seed, every statement here runs with foreign keys, checks, and
unique constraints enforced, because this is the path the Collection Worker
would use.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import sqlalchemy as sa

from . import config
from .generate import RECORDS_PER_RUN, card_uuid, h, idempotency_key, price_for

# Identifier space reserved for rows created at runtime, so generated seed ids
# and writer ids never collide.
ID_BASE = {
    "ingest_run": 1_000_000_000_000,
    "raw_artifact": 2_000_000_000_000,
    "processing_run": 3_000_000_000_000,
    "extracted_record": 4_000_000_000_000,
    "observation_candidate": 5_000_000_000_000,
    "identity_resolution_attempt": 6_000_000_000_000,
    "price_observation": 7_000_000_000_000,
    "review_item": 8_000_000_000_000,
}
WRITER_STRIDE = 10_000_000_000


def _id(table: str, writer_id: int, counter: int) -> int:
    return ID_BASE[table] + writer_id * WRITER_STRIDE + counter


def next_sequence(eng: sa.Engine, writer_id: int) -> int:
    """Continue a writer's identifier range instead of colliding with an earlier run."""

    low = ID_BASE["ingest_run"] + writer_id * WRITER_STRIDE
    with eng.connect() as conn:
        highest = conn.execute(
            sa.text("SELECT MAX(id) FROM ingest_run WHERE id >= :low AND id < :high"),
            {"low": low, "high": low + WRITER_STRIDE},
        ).scalar()
    return 0 if highest is None else int(highest) - low


INSERTS = {
    "ingest_run": (
        "INSERT INTO ingest_run (id, source_id, started_at, finished_at, status,"
        " fetched_count, parsed_count, stored_count, error_class)"
        " VALUES (:id, :source_id, :started_at, :finished_at, :status, :fetched_count,"
        " :parsed_count, :stored_count, NULL)"
    ),
    "raw_artifact": (
        "INSERT INTO raw_artifact (id, ingest_run_id, source_id, source_item_id, url,"
        " mime_type, content_hash, byte_size, fetched_at, published_at, storage_ref)"
        " VALUES (:id, :ingest_run_id, :source_id, :source_item_id, :url, :mime_type,"
        " :content_hash, :byte_size, :fetched_at, NULL, :storage_ref)"
    ),
    "processing_run": (
        "INSERT INTO processing_run (id, raw_artifact_id, processor_name, processor_version,"
        " config_ref, attempt_no, started_at, finished_at, status, extracted_count,"
        " promoted_count, error_class)"
        " VALUES (:id, :raw_artifact_id, :processor_name, :processor_version, :config_ref,"
        " :attempt_no, :started_at, :finished_at, 'succeeded', :extracted_count,"
        " :promoted_count, NULL)"
    ),
    "extracted_record": (
        "INSERT INTO extracted_record (id, processing_run_id, raw_artifact_id, locator, payload,"
        " value_origin, confidence, warnings, created_at)"
        " VALUES (:id, :processing_run_id, :raw_artifact_id, :locator, :payload, :value_origin,"
        " :confidence, NULL, :created_at)"
    ),
    "observation_candidate": (
        "INSERT INTO observation_candidate (id, extracted_record_id, shop_id, source_id, tcg,"
        " amount_minor, currency, price_type, raw_card_name, raw_card_number, raw_set,"
        " raw_rarity, raw_edition, raw_language, raw_condition, observed_at,"
        " promotion_rule_version, created_at)"
        " VALUES (:id, :extracted_record_id, :shop_id, :source_id, :tcg, :amount_minor,"
        " :currency, :price_type, :raw_card_name, :raw_card_number, :raw_set, :raw_rarity,"
        " :raw_edition, :raw_language, :raw_condition, :observed_at, :promotion_rule_version,"
        " :created_at)"
    ),
    "identity_resolution_attempt": (
        "INSERT INTO identity_resolution_attempt (id, observation_candidate_id, matcher_name,"
        " matcher_version, card_identity_id, match_score, result, evidence, created_at)"
        " VALUES (:id, :observation_candidate_id, :matcher_name, :matcher_version,"
        " :card_identity_id, :match_score, :result, :evidence, :created_at)"
    ),
    "review_item": (
        "INSERT INTO review_item (id, ingest_run_id, raw_artifact_id, extracted_record_id,"
        " identity_resolution_attempt_id, reason, state, priority, created_at, decided_at,"
        " decided_by, decision, lock_version)"
        " VALUES (:id, :ingest_run_id, :raw_artifact_id, :extracted_record_id, NULL, :reason,"
        " 'pending', :priority, :created_at, NULL, NULL, NULL, 0)"
    ),
}

OBSERVATION_COLUMNS = (
    "id, observation_candidate_id, card_identity_id, shop_id, source_id, raw_artifact_id, tcg,"
    " amount_minor, currency, price_type, card_condition, observed_at, collected_at,"
    " published_at, valid_until, idempotency_key, created_at"
)
OBSERVATION_VALUES = (
    "(:id, :observation_candidate_id, :card_identity_id, :shop_id, :source_id, :raw_artifact_id,"
    " :tcg, :amount_minor, :currency, :price_type, :card_condition, :observed_at, :collected_at,"
    " NULL, NULL, :idempotency_key, :created_at)"
)


def observation_insert(engine_name: str, idempotent: bool = True) -> str:
    """Append an observation, ignoring an existing idempotency key.

    PostgreSQL names the unique constraint it must ignore, which needs only the
    INSERT privilege. MariaDB has no equivalent: ``INSERT IGNORE`` downgrades
    every error in the statement to a warning, and ``ON DUPLICATE KEY UPDATE``
    requires the UPDATE privilege that an append-only role must not hold. There
    the caller inserts plainly and treats a duplicate key as success.
    """

    base = f"INSERT INTO price_observation ({OBSERVATION_COLUMNS}) VALUES {OBSERVATION_VALUES}"
    if idempotent and engine_name == "postgres":
        return base + " ON CONFLICT (idempotency_key) DO NOTHING"
    return base


def is_duplicate_key(exc: BaseException) -> bool:
    orig = getattr(exc, "orig", exc)
    sqlstate = getattr(orig, "sqlstate", None)
    if sqlstate is None:
        diag = getattr(orig, "diag", None)
        sqlstate = getattr(diag, "sqlstate", None) if diag else None
    if sqlstate == "23505":
        return True
    args = getattr(orig, "args", ())
    return bool(args) and args[0] == 1062


def insert_observations(conn: sa.Connection, engine_name: str, rows: list[dict],
                        idempotent: bool = True) -> int:
    """Append observations, skipping rows whose idempotency key already exists."""

    if not rows:
        return 0
    statement = sa.text(observation_insert(engine_name, idempotent))
    if engine_name == "postgres" or not idempotent:
        return conn.execute(statement, rows).rowcount
    try:
        return conn.execute(statement, rows).rowcount
    except sa.exc.IntegrityError as exc:
        if not is_duplicate_key(exc):
            raise
    inserted = 0
    for row in rows:
        savepoint = conn.begin_nested()
        try:
            conn.execute(statement, row)
        except sa.exc.IntegrityError as inner:
            savepoint.rollback()
            if not is_duplicate_key(inner):
                raise
        else:
            savepoint.commit()
            inserted += 1
    return inserted


def _payload_text(card_index: int, amount: int, condition: str) -> str:
    return (
        '{"name":"card%d","price_text":"¥%d","condition":"%s","stock":%d}'
        % (card_index, amount, condition, card_index % 9)
    )


def materialize_artifact(artifact_root: Path, storage_ref: str, payload: dict) -> None:
    """Store the artifact body before its metadata is committed.

    The data model requires artifact metadata to be confirmed only after the
    body is stored, and restore verification checks that every referenced
    artifact exists.
    """

    target = artifact_root / storage_ref.removeprefix("artifacts/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")


def build_batch(writer_id: int, seq: int, rows: int, cards: int,
                observed_at: datetime | None = None, tag: str = "run",
                artifact_root: Path | None = None) -> dict[str, Any]:
    """Build one artifact's worth of ingestion rows without touching the database."""

    observed = observed_at or datetime.now(UTC).replace(tzinfo=None)
    if observed.tzinfo is not None:
        observed = observed.astimezone(UTC).replace(tzinfo=None)
    source_id = (writer_id + seq) % 4 + 1
    slug = config.SOURCES[source_id - 1][1]
    run_id = _id("ingest_run", writer_id, seq)
    artifact_id = _id("raw_artifact", writer_id, seq)
    processing_id = _id("processing_run", writer_id, seq)

    ingest_run = {
        "id": run_id, "source_id": source_id, "started_at": observed,
        "finished_at": observed + timedelta(minutes=1), "status": "succeeded",
        "fetched_count": rows, "parsed_count": rows, "stored_count": rows,
    }
    artifact = {
        "id": artifact_id, "ingest_run_id": run_id, "source_id": source_id,
        "source_item_id": f"{tag}-{writer_id}-{seq}",
        "url": f"https://example.invalid/{slug}/{tag}/{seq}",
        "mime_type": "application/json",
        "content_hash": f"{h(artifact_id):08x}{h(artifact_id + 1):08x}"
                        f"{h(artifact_id + 2):08x}{h(artifact_id + 3):08x}"
                        f"{h(artifact_id + 4):08x}{h(artifact_id + 5):08x}"
                        f"{h(artifact_id + 6):08x}{h(artifact_id + 7):08x}",
        "byte_size": 1024 + seq % 4096, "fetched_at": observed,
        "storage_ref": f"artifacts/runtime/{writer_id}/{seq}.json",
    }
    processing_run = {
        "id": processing_id, "raw_artifact_id": artifact_id,
        "processor_name": "price_table_parser", "processor_version": "1.0.0",
        "config_ref": "config/v1", "attempt_no": 1, "started_at": observed,
        "finished_at": observed + timedelta(seconds=2), "extracted_count": rows,
        "promoted_count": rows,
    }

    records, candidates, attempts, observations, reviews = [], [], [], [], []
    for i in range(rows):
        counter = seq * RECORDS_PER_RUN + i
        record_id = _id("extracted_record", writer_id, counter)
        candidate_id = _id("observation_candidate", writer_id, counter)
        observation_id = _id("price_observation", writer_id, counter)
        card_index = h(record_id) % cards
        amount = price_for(record_id)
        condition = config.CONDITIONS[h(record_id + 5) % len(config.CONDITIONS)]
        price_type = "buy" if h(record_id + 3) % 4 else "sell"
        records.append({
            "id": record_id, "processing_run_id": processing_id, "raw_artifact_id": artifact_id,
            "locator": f"$.items[{i}]", "payload": _payload_text(card_index, amount, condition),
            "value_origin": "artifact", "confidence": 0.98, "created_at": observed,
        })
        candidates.append({
            "id": candidate_id, "extracted_record_id": record_id, "shop_id": source_id,
            "source_id": source_id, "tcg": config.TCG, "amount_minor": amount,
            "currency": config.CURRENCY, "price_type": price_type,
            "raw_card_name": f"card{card_index}", "raw_card_number": f"{card_index % 1000:03d}/165",
            "raw_set": f"SV{card_index // 1000:03d}", "raw_rarity": "RR", "raw_edition": "1st",
            "raw_language": "ja", "raw_condition": condition, "observed_at": observed,
            "promotion_rule_version": "v1", "created_at": observed,
        })
        attempts.append({
            "id": _id("identity_resolution_attempt", writer_id, counter * 2),
            "observation_candidate_id": candidate_id, "matcher_name": "attribute_matcher",
            "matcher_version": "1.0.0", "card_identity_id": card_uuid(card_index),
            "match_score": 0.99, "result": "confirmed", "evidence": "set+number+rarity",
            "created_at": observed,
        })
        attempts.append({
            "id": _id("identity_resolution_attempt", writer_id, counter * 2 + 1),
            "observation_candidate_id": candidate_id, "matcher_name": "attribute_matcher",
            "matcher_version": "1.0.0", "card_identity_id": card_uuid((card_index + 7) % cards),
            "match_score": 0.55, "result": "rejected", "evidence": "name_similarity",
            "created_at": observed,
        })
        observations.append({
            "id": observation_id, "observation_candidate_id": candidate_id,
            "card_identity_id": card_uuid(card_index), "shop_id": source_id,
            "source_id": source_id, "raw_artifact_id": artifact_id, "tcg": config.TCG,
            "amount_minor": amount, "currency": config.CURRENCY, "price_type": price_type,
            "card_condition": condition, "observed_at": observed, "collected_at": observed,
            "idempotency_key": idempotency_key(slug, artifact_id, i, price_type,
                                               observed.strftime("%Y-%m-%d"), condition),
            "created_at": observed,
        })
        if i % 10 == 0:
            reviews.append({
                "id": _id("review_item", writer_id, counter), "ingest_run_id": run_id,
                "raw_artifact_id": artifact_id, "extracted_record_id": record_id,
                "reason": "parse_ambiguous", "priority": (i % 5) + 1, "created_at": observed,
            })

    if artifact_root is not None:
        materialize_artifact(artifact_root, artifact["storage_ref"],
                             {"artifact": artifact["source_item_id"], "rows": rows})

    return {
        "ingest_run": [ingest_run], "raw_artifact": [artifact],
        "processing_run": [processing_run], "extracted_record": records,
        "observation_candidate": candidates, "identity_resolution_attempt": attempts,
        "price_observation": observations, "review_item": reviews,
    }


def write_batch(conn: sa.Connection, engine_name: str, batch: dict[str, list[dict]],
                idempotent: bool = True) -> dict[str, int]:
    """Insert one prepared batch inside the caller's transaction."""

    counts: dict[str, int] = {}
    for table in ("ingest_run", "raw_artifact", "processing_run", "extracted_record",
                  "observation_candidate", "identity_resolution_attempt"):
        rows = batch.get(table) or []
        if rows:
            conn.execute(sa.text(INSERTS[table]), rows)
        counts[table] = len(rows)
    observations = batch.get("price_observation") or []
    insert_observations(conn, engine_name, observations, idempotent)
    counts["price_observation"] = len(observations)
    reviews = batch.get("review_item") or []
    if reviews:
        conn.execute(sa.text(INSERTS["review_item"]), reviews)
    counts["review_item"] = len(reviews)
    return counts


def insert_observation_batch(eng: sa.Engine, engine_name: str, tag: str = "run",
                             batch: int = 20, offset: int = 0, writer_id: int = 90,
                             cards: int = 12_000, seq_start: int = 0,
                             artifact_root: Path | None = None) -> int:
    """Append one small batch and commit; used by background writers."""

    payload = build_batch(writer_id, seq_start + offset + 1, batch, cards, tag=tag,
                          artifact_root=artifact_root)
    with eng.begin() as conn:
        counts = write_batch(conn, engine_name, payload)
    return counts["price_observation"]


def reparse_batches(writer_id: int, artifact_ids: Iterable[int], rows: int, cards: int,
                    observed_at: datetime) -> Iterable[dict[str, Any]]:
    """Rebuild rows for stored artifacts as a second processing attempt.

    The observations carry the same idempotency keys as the first pass, so a
    correct database must keep exactly one confirmed observation per key.
    """

    for seq, artifact_id in enumerate(artifact_ids):
        batch = build_batch(writer_id, seq, rows, cards, observed_at=observed_at, tag="reparse")
        batch["raw_artifact"] = []
        batch["ingest_run"] = []
        batch["review_item"] = []
        batch["processing_run"][0]["raw_artifact_id"] = artifact_id
        batch["processing_run"][0]["attempt_no"] = 2
        for record in batch["extracted_record"]:
            record["raw_artifact_id"] = artifact_id
        for observation in batch["price_observation"]:
            observation["raw_artifact_id"] = artifact_id
        yield batch
