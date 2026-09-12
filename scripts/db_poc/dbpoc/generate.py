"""Deterministic data generator for the CP-0009 load profiles.

The same files feed both candidates, so any difference in load time or size
comes from the database and not from the data. Rows are written as tab
separated text in PostgreSQL ``COPY`` text format, which MariaDB's
``LOAD DATA ... FIELDS TERMINATED BY '\\t' ESCAPED BY '\\\\'`` reads with the
same escaping and the same ``\\N`` NULL marker.

Values are derived from a multiplicative hash of the row index instead of a
random number generator, so any row can be regenerated independently and the
files are byte-identical between runs.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import config
from .util import Result, timer

NAMESPACE = uuid.UUID("6b3f2f4e-0f4b-4a2a-9a0f-1d6f5c3f9b21")
BASE_DAY = datetime(2026, 8, 15, tzinfo=UTC)  # 28-day window ends 2026-09-11
HISTORY_ID_OFFSET = 900_000_000
HISTORY_RUN_OFFSET = 9_000_000

SET_PREFIX = "SV"
RARITIES = ("C", "U", "R", "RR", "SR", "SAR", "UR")
EDITIONS = ("1st", "unlimited")
LANGUAGES = ("ja", "en")
NAME_HEAD = ("ピカチュウ", "リザードン", "ミュウツー", "ルギア", "ゲンガー", "カビゴン",
             "イーブイ", "ミライドン", "コライドン", "ギラティナ")
NAME_TAIL = ("ex", "V", "VMAX", "VSTAR", "", "GX", "AR")
MIME_TYPES = ("application/json", "text/html", "text/csv")
REVIEW_REASONS_PENDING = ("parse_ambiguous", "price_out_of_range", "missing_condition")

COLUMNS = {
    "card_identity": ("id", "tcg", "set_code", "card_number", "rarity", "edition", "language",
                      "normalized_name", "created_at"),
    "ingest_run": ("id", "source_id", "started_at", "finished_at", "status", "fetched_count",
                   "parsed_count", "stored_count", "error_class"),
    "raw_artifact": ("id", "ingest_run_id", "source_id", "source_item_id", "url", "mime_type",
                     "content_hash", "byte_size", "fetched_at", "published_at", "storage_ref"),
    "processing_run": ("id", "raw_artifact_id", "processor_name", "processor_version",
                       "config_ref", "attempt_no", "started_at", "finished_at", "status",
                       "extracted_count", "promoted_count", "error_class"),
    "extracted_record": ("id", "processing_run_id", "raw_artifact_id", "locator", "payload",
                         "value_origin", "confidence", "warnings", "created_at"),
    "observation_candidate": ("id", "extracted_record_id", "shop_id", "source_id", "tcg",
                              "amount_minor", "currency", "price_type", "raw_card_name",
                              "raw_card_number", "raw_set", "raw_rarity", "raw_edition",
                              "raw_language", "raw_condition", "observed_at",
                              "promotion_rule_version", "created_at"),
    "identity_resolution_attempt": ("id", "observation_candidate_id", "matcher_name",
                                    "matcher_version", "card_identity_id", "match_score",
                                    "result", "evidence", "created_at"),
    "price_observation": ("id", "observation_candidate_id", "card_identity_id", "shop_id",
                          "source_id", "raw_artifact_id", "tcg", "amount_minor", "currency",
                          "price_type", "card_condition", "observed_at", "collected_at",
                          "published_at", "valid_until", "idempotency_key", "created_at"),
    "review_item": ("id", "ingest_run_id", "raw_artifact_id", "extracted_record_id",
                    "identity_resolution_attempt_id", "reason", "state", "priority",
                    "created_at", "decided_at", "decided_by", "decision", "lock_version"),
}

RECORDS_PER_RUN = 60  # 840,000 extracted rows / 14,000 artifacts per scale unit


def h(value: int) -> int:
    """Cheap deterministic hash used instead of a random number generator."""

    x = (value * 2654435761) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 2246822519) & 0xFFFFFFFF
    x ^= x >> 13
    return x


def card_uuid(index: int) -> str:
    return str(uuid.uuid5(NAMESPACE, f"card:{index}"))


def ts(moment: datetime) -> str:
    """UTC timestamp both loaders accept (sessions are pinned to UTC)."""

    return moment.strftime("%Y-%m-%d %H:%M:%S.%f")


def price_for(index: int) -> int:
    """Skewed JPY price: most cards are cheap, a few are very expensive."""

    bucket = h(index * 7 + 11) % 1000
    if bucket < 700:
        return 50 + h(index) % 1200
    if bucket < 950:
        return 1_200 + h(index * 3) % 12_000
    if bucket < 999:
        return 13_000 + h(index * 5) % 90_000
    return 100_000 + h(index * 13) % 400_000


def out_dir(scale: int) -> Path:
    directory = config.DATA_DIR / f"scale{scale}"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _writer(path: Path):
    return path.open("w", encoding="utf-8", buffering=1 << 20)


def gen_card_identity(scale: int) -> tuple[str, int]:
    profile = config.PROFILES[scale]
    path = out_dir(scale) / "card_identity.tsv"
    created = ts(BASE_DAY - timedelta(days=400))
    with _writer(path) as fh:
        chunk: list[str] = []
        for i in range(profile.cards):
            hv = h(i)
            name = f"{NAME_HEAD[hv % len(NAME_HEAD)]}{NAME_TAIL[(hv >> 4) % len(NAME_TAIL)]}"
            chunk.append(
                f"{card_uuid(i)}\t{config.TCG}\t{SET_PREFIX}{i // 1000:03d}\t"
                f"{i % 1000:03d}/165\t{RARITIES[hv % len(RARITIES)]}\t"
                f"{EDITIONS[(hv >> 8) % len(EDITIONS)]}\t{LANGUAGES[(hv >> 12) % len(LANGUAGES)]}\t"
                f"{name}{i}\t{created}\n"
            )
            if len(chunk) >= 50_000:
                fh.write("".join(chunk))
                chunk.clear()
        fh.write("".join(chunk))
    return "card_identity", profile.cards


def gen_ingest_run(scale: int) -> tuple[str, int]:
    profile = config.PROFILES[scale]
    path = out_dir(scale) / "ingest_run.tsv"
    slots = 4 * scale
    rows = 0
    with _writer(path) as fh:
        chunk = []
        for day in range(profile.days):
            for slot in range(slots):
                run_id = day * slots + slot + 1
                started = BASE_DAY + timedelta(days=day, hours=3, minutes=slot % 60)
                finished = started + timedelta(minutes=12)
                status = "succeeded" if h(run_id) % 50 else "partial"
                chunk.append(
                    f"{run_id}\t{slot % 4 + 1}\t{ts(started)}\t{ts(finished)}\t{status}\t"
                    f"{500}\t{500}\t{500}\t" + ("\\N" if status == "succeeded" else "parser_error")
                    + "\n"
                )
                rows += 1
        # One year of representative history: one run per day and source.
        for day in range(profile.history_days):
            for slot in range(profile.history_shops):
                run_id = HISTORY_RUN_OFFSET + day * profile.history_shops + slot + 1
                started = BASE_DAY - timedelta(days=profile.history_days - day) + timedelta(hours=3)
                chunk.append(
                    f"{run_id}\t{slot + 1}\t{ts(started)}\t{ts(started + timedelta(minutes=5))}\t"
                    f"succeeded\t200\t200\t200\t\\N\n"
                )
                rows += 1
        fh.write("".join(chunk))
    return "ingest_run", rows


def gen_raw_artifact(scale: int) -> tuple[str, int]:
    profile = config.PROFILES[scale]
    path = out_dir(scale) / "raw_artifact.tsv"
    per_day = 500 * scale
    slots = 4 * scale
    rows = 0
    with _writer(path) as fh:
        chunk = []
        for i in range(profile.raw_artifact):
            day, offset = divmod(i, per_day)
            slot = offset % slots
            source_id = slot % 4 + 1
            run_id = day * slots + slot + 1
            hv = h(i + 1)
            fetched = BASE_DAY + timedelta(days=day, hours=3, seconds=offset % 3600)
            digest = f"{hv:08x}{h(i + 2):08x}{h(i + 3):08x}{h(i + 4):08x}"[:56] + f"{i:08x}"
            shard = f"{i % 256:02x}"
            url = f"https://example.invalid/{config.SOURCES[source_id - 1][1]}/page/{i}"
            chunk.append(
                f"{i + 1}\t{run_id}\t{source_id}\t{config.SOURCES[source_id - 1][1]}-{i}\t{url}\t"
                f"{MIME_TYPES[hv % len(MIME_TYPES)]}\t{digest}\t{5000 + hv % 2_000_000}\t"
                f"{ts(fetched)}\t\\N\tartifacts/{shard}/{i}.json\n"
            )
            rows += 1
            if len(chunk) >= 50_000:
                fh.write("".join(chunk))
                chunk.clear()
        for day in range(profile.history_days):
            for slot in range(profile.history_shops):
                index = day * profile.history_shops + slot
                artifact_id = HISTORY_ID_OFFSET + index + 1
                run_id = HISTORY_RUN_OFFSET + index + 1
                fetched = BASE_DAY - timedelta(days=profile.history_days - day) + timedelta(hours=3)
                digest = f"{h(artifact_id):08x}" * 7 + f"{index:08x}"
                chunk.append(
                    f"{artifact_id}\t{run_id}\t{slot + 1}\thistory-{index}\t"
                    f"https://example.invalid/history/{index}\tapplication/json\t{digest[:64]}\t"
                    f"{120_000}\t{ts(fetched)}\t\\N\tartifacts/hi/{index}.json\n"
                )
                rows += 1
        fh.write("".join(chunk))
    return "raw_artifact", rows


def gen_processing_run(scale: int) -> tuple[str, int]:
    profile = config.PROFILES[scale]
    path = out_dir(scale) / "processing_run.tsv"
    per_day = 500 * scale
    rows = 0
    with _writer(path) as fh:
        chunk = []
        for i in range(profile.raw_artifact):
            day, offset = divmod(i, per_day)
            started = BASE_DAY + timedelta(days=day, hours=4, seconds=offset % 3600)
            chunk.append(
                f"{i + 1}\t{i + 1}\tprice_table_parser\t1.0.0\tconfig/v1\t1\t{ts(started)}\t"
                f"{ts(started + timedelta(seconds=8))}\tsucceeded\t{RECORDS_PER_RUN}\t"
                f"{RECORDS_PER_RUN}\t\\N\n"
            )
            rows += 1
            if len(chunk) >= 50_000:
                fh.write("".join(chunk))
                chunk.clear()
        for index in range(profile.history_days * profile.history_shops):
            run_id = HISTORY_ID_OFFSET + index + 1
            started = BASE_DAY - timedelta(days=profile.history_days) + timedelta(
                days=index // profile.history_shops, hours=4)
            chunk.append(
                f"{run_id}\t{run_id}\tprice_table_parser\t1.0.0\tconfig/v1\t1\t{ts(started)}\t"
                f"{ts(started + timedelta(seconds=4))}\tsucceeded\t{profile.history_cards}\t"
                f"{profile.history_cards}\t\\N\n"
            )
            rows += 1
        fh.write("".join(chunk))
    return "processing_run", rows


def _payload(record_index: int, card_index: int, amount: int, condition: str) -> str:
    hv = h(card_index)
    name = f"{NAME_HEAD[hv % len(NAME_HEAD)]}{NAME_TAIL[(hv >> 4) % len(NAME_TAIL)]}{card_index}"
    return json.dumps(
        {
            "row": record_index % RECORDS_PER_RUN,
            "name": name,
            "number": f"{card_index % 1000:03d}/165",
            "set": f"{SET_PREFIX}{card_index // 1000:03d}",
            "price_text": f"¥{amount:,}",
            "condition": condition,
            "stock": h(record_index) % 9,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _card_for(record_index: int, cards: int) -> int:
    return h(record_index * 31 + 7) % cards


def gen_extracted_record(scale: int) -> tuple[str, int]:
    profile = config.PROFILES[scale]
    path = out_dir(scale) / "extracted_record.tsv"
    per_day = 500 * scale
    rows = 0
    with _writer(path) as fh:
        chunk = []
        for i in range(profile.extracted_record):
            run_index = i // RECORDS_PER_RUN
            day, offset = divmod(run_index, per_day)
            created = BASE_DAY + timedelta(days=day, hours=4, seconds=offset % 3600)
            card_index = _card_for(i, profile.cards)
            amount = price_for(i)
            condition = config.CONDITIONS[h(i + 5) % len(config.CONDITIONS)]
            hv = h(i + 9)
            origin = "artifact" if hv % 10 else "ingest_config"
            confidence = "\\N" if hv % 17 == 0 else f"{0.90 + (hv % 100) / 1000:.4f}"
            warnings = "\\N" if hv % 23 else "ambiguous_condition"
            chunk.append(
                f"{i + 1}\t{run_index + 1}\t{run_index + 1}\t$.items[{i % RECORDS_PER_RUN}]\t"
                f"{_payload(i, card_index, amount, condition)}\t{origin}\t{confidence}\t{warnings}\t"
                f"{ts(created)}\n"
            )
            rows += 1
            if len(chunk) >= 50_000:
                fh.write("".join(chunk))
                chunk.clear()
        fh.write("".join(chunk))
        chunk.clear()
        # Representative history: 200 cards x 365 days x 3 shops.
        for index in range(profile.history_rows):
            day, rest = divmod(index, profile.history_cards * profile.history_shops)
            shop_slot, card_index = divmod(rest, profile.history_cards)
            run_id = HISTORY_ID_OFFSET + day * profile.history_shops + shop_slot + 1
            created = BASE_DAY - timedelta(days=profile.history_days - day) + timedelta(hours=4)
            amount = price_for(card_index * 1000 + day)
            condition = config.CONDITIONS[h(card_index) % len(config.CONDITIONS)]
            chunk.append(
                f"{HISTORY_ID_OFFSET + index + 1}\t{run_id}\t{run_id}\t$.items[{card_index}]\t"
                f"{_payload(index, card_index, amount, condition)}\tartifact\t0.9900\t\\N\t"
                f"{ts(created)}\n"
            )
            rows += 1
            if len(chunk) >= 50_000:
                fh.write("".join(chunk))
                chunk.clear()
        fh.write("".join(chunk))
    return "extracted_record", rows


def gen_observation_candidate(scale: int) -> tuple[str, int]:
    profile = config.PROFILES[scale]
    path = out_dir(scale) / "observation_candidate.tsv"
    per_day = 500 * scale
    rows = 0
    with _writer(path) as fh:
        chunk = []
        for i in range(profile.observation_candidate):
            run_index = i // RECORDS_PER_RUN
            day, offset = divmod(run_index, per_day)
            source_id = (offset % (4 * scale)) % 4 + 1
            observed = BASE_DAY + timedelta(days=day, hours=3, seconds=offset % 3600)
            card_index = _card_for(i, profile.cards)
            hv = h(card_index)
            amount = price_for(i)
            condition = config.CONDITIONS[h(i + 5) % len(config.CONDITIONS)]
            price_type = "buy" if h(i + 3) % 4 else "sell"
            name = f"{NAME_HEAD[hv % len(NAME_HEAD)]}{NAME_TAIL[(hv >> 4) % len(NAME_TAIL)]}{card_index}"
            chunk.append(
                f"{i + 1}\t{i + 1}\t{source_id}\t{source_id}\t{config.TCG}\t{amount}\t"
                f"{config.CURRENCY}\t{price_type}\t{name}\t{card_index % 1000:03d}/165\t"
                f"{SET_PREFIX}{card_index // 1000:03d}\t{RARITIES[hv % len(RARITIES)]}\t"
                f"{EDITIONS[(hv >> 8) % len(EDITIONS)]}\t{LANGUAGES[(hv >> 12) % len(LANGUAGES)]}\t"
                f"{condition}\t{ts(observed)}\tv1\t{ts(observed)}\n"
            )
            rows += 1
            if len(chunk) >= 50_000:
                fh.write("".join(chunk))
                chunk.clear()
        fh.write("".join(chunk))
        chunk.clear()
        for index in range(profile.history_rows):
            day, rest = divmod(index, profile.history_cards * profile.history_shops)
            shop_slot, card_index = divmod(rest, profile.history_cards)
            observed = BASE_DAY - timedelta(days=profile.history_days - day) + timedelta(hours=3)
            hv = h(card_index)
            amount = price_for(card_index * 1000 + day)
            condition = config.CONDITIONS[h(card_index) % len(config.CONDITIONS)]
            name = f"{NAME_HEAD[hv % len(NAME_HEAD)]}{NAME_TAIL[(hv >> 4) % len(NAME_TAIL)]}{card_index}"
            chunk.append(
                f"{HISTORY_ID_OFFSET + index + 1}\t{HISTORY_ID_OFFSET + index + 1}\t"
                f"{shop_slot + 1}\t{shop_slot + 1}\t{config.TCG}\t{amount}\t{config.CURRENCY}\tbuy\t"
                f"{name}\t{card_index % 1000:03d}/165\t{SET_PREFIX}{card_index // 1000:03d}\t"
                f"{RARITIES[hv % len(RARITIES)]}\t{EDITIONS[(hv >> 8) % len(EDITIONS)]}\t"
                f"{LANGUAGES[(hv >> 12) % len(LANGUAGES)]}\t{condition}\t{ts(observed)}\tv1\t"
                f"{ts(observed)}\n"
            )
            rows += 1
            if len(chunk) >= 50_000:
                fh.write("".join(chunk))
                chunk.clear()
        fh.write("".join(chunk))
    return "observation_candidate", rows


def gen_identity_resolution_attempt(scale: int) -> tuple[str, int]:
    profile = config.PROFILES[scale]
    path = out_dir(scale) / "identity_resolution_attempt.tsv"
    per_day = 500 * scale
    rows = 0
    with _writer(path) as fh:
        chunk = []
        for i in range(profile.observation_candidate):
            run_index = i // RECORDS_PER_RUN
            day, offset = divmod(run_index, per_day)
            created = BASE_DAY + timedelta(days=day, hours=5, seconds=offset % 3600)
            card_index = _card_for(i, profile.cards)
            other = (card_index + 1 + h(i) % 97) % profile.cards
            confirmed_score = f"{0.9700 + (h(i) % 30) / 1000:.4f}"
            rejected_score = f"{0.4000 + (h(i + 1) % 400) / 1000:.4f}"
            chunk.append(
                f"{2 * i + 1}\t{i + 1}\tattribute_matcher\t1.0.0\t{card_uuid(card_index)}\t"
                f"{confirmed_score}\tconfirmed\tset+number+rarity\t{ts(created)}\n"
                f"{2 * i + 2}\t{i + 1}\tattribute_matcher\t1.0.0\t{card_uuid(other)}\t"
                f"{rejected_score}\trejected\tname_similarity\t{ts(created)}\n"
            )
            rows += 2
            if len(chunk) >= 25_000:
                fh.write("".join(chunk))
                chunk.clear()
        fh.write("".join(chunk))
        chunk.clear()
        for index in range(profile.history_rows):
            day, rest = divmod(index, profile.history_cards * profile.history_shops)
            _, card_index = divmod(rest, profile.history_cards)
            created = BASE_DAY - timedelta(days=profile.history_days - day) + timedelta(hours=5)
            base_id = HISTORY_ID_OFFSET * 2 + 2 * index
            other = (card_index + 3) % profile.cards
            chunk.append(
                f"{base_id + 1}\t{HISTORY_ID_OFFSET + index + 1}\tattribute_matcher\t1.0.0\t"
                f"{card_uuid(card_index)}\t0.9900\tconfirmed\tset+number+rarity\t{ts(created)}\n"
                f"{base_id + 2}\t{HISTORY_ID_OFFSET + index + 1}\tattribute_matcher\t1.0.0\t"
                f"{card_uuid(other)}\t0.5100\trejected\tname_similarity\t{ts(created)}\n"
            )
            rows += 2
            if len(chunk) >= 25_000:
                fh.write("".join(chunk))
                chunk.clear()
        fh.write("".join(chunk))
    return "identity_resolution_attempt", rows


def idempotency_key(source_slug: str, artifact_index: int, row: int, price_type: str,
                    observed_date: str, condition: str) -> str:
    return f"{source_slug}|{artifact_index}|{row}|{price_type}|{observed_date}|{condition}"


def observation_fields(i: int, scale: int) -> dict:
    """The observation the generator derives from extracted row ``i``.

    Reparsing stored artifacts must produce the same values, so both the
    generator and the reparse workload read them from here.
    """

    profile = config.PROFILES[scale]
    per_day = 500 * scale
    run_index = i // RECORDS_PER_RUN
    day, offset = divmod(run_index, per_day)
    source_id = (offset % (4 * scale)) % 4 + 1
    slug = config.SOURCES[source_id - 1][1]
    observed = BASE_DAY + timedelta(days=day, hours=3, seconds=offset % 3600)
    card_index = _card_for(i, profile.cards)
    amount = price_for(i)
    condition = config.CONDITIONS[h(i + 5) % len(config.CONDITIONS)]
    price_type = "buy" if h(i + 3) % 4 else "sell"
    return {
        "run_index": run_index,
        "row": i % RECORDS_PER_RUN,
        "source_id": source_id,
        "slug": slug,
        "observed": observed,
        "card_index": card_index,
        "amount": amount,
        "condition": condition,
        "price_type": price_type,
        "idempotency_key": idempotency_key(slug, run_index, i % RECORDS_PER_RUN, price_type,
                                           observed.strftime("%Y-%m-%d"), condition),
    }


def gen_price_observation(scale: int) -> tuple[str, int]:
    profile = config.PROFILES[scale]
    path = out_dir(scale) / "price_observation.tsv"
    per_day = 500 * scale
    rows = 0
    with _writer(path) as fh:
        chunk = []
        for i in range(profile.price_observation):
            run_index = i // RECORDS_PER_RUN
            day, offset = divmod(run_index, per_day)
            source_id = (offset % (4 * scale)) % 4 + 1
            slug = config.SOURCES[source_id - 1][1]
            observed = BASE_DAY + timedelta(days=day, hours=3, seconds=offset % 3600)
            collected = observed + timedelta(minutes=6)
            card_index = _card_for(i, profile.cards)
            amount = price_for(i)
            condition = config.CONDITIONS[h(i + 5) % len(config.CONDITIONS)]
            price_type = "buy" if h(i + 3) % 4 else "sell"
            key = idempotency_key(slug, run_index, i % RECORDS_PER_RUN, price_type,
                                  observed.strftime("%Y-%m-%d"), condition)
            chunk.append(
                f"{i + 1}\t{i + 1}\t{card_uuid(card_index)}\t{source_id}\t{source_id}\t"
                f"{run_index + 1}\t{config.TCG}\t{amount}\t{config.CURRENCY}\t{price_type}\t"
                f"{condition}\t{ts(observed)}\t{ts(collected)}\t\\N\t\\N\t{key}\t{ts(collected)}\n"
            )
            rows += 1
            if len(chunk) >= 50_000:
                fh.write("".join(chunk))
                chunk.clear()
        fh.write("".join(chunk))
        chunk.clear()
        for index in range(profile.history_rows):
            day, rest = divmod(index, profile.history_cards * profile.history_shops)
            shop_slot, card_index = divmod(rest, profile.history_cards)
            observed = BASE_DAY - timedelta(days=profile.history_days - day) + timedelta(hours=3)
            amount = price_for(card_index * 1000 + day)
            condition = config.CONDITIONS[h(card_index) % len(config.CONDITIONS)]
            slug = config.SOURCES[shop_slot][1]
            key = idempotency_key(slug, HISTORY_ID_OFFSET + index, card_index, "buy",
                                  observed.strftime("%Y-%m-%d"), condition)
            chunk.append(
                f"{HISTORY_ID_OFFSET + index + 1}\t{HISTORY_ID_OFFSET + index + 1}\t"
                f"{card_uuid(card_index)}\t{shop_slot + 1}\t{shop_slot + 1}\t"
                f"{HISTORY_ID_OFFSET + day * profile.history_shops + shop_slot + 1}\t"
                f"{config.TCG}\t{amount}\t{config.CURRENCY}\tbuy\t{condition}\t{ts(observed)}\t"
                f"{ts(observed + timedelta(minutes=6))}\t\\N\t\\N\t{key}\t"
                f"{ts(observed + timedelta(minutes=6))}\n"
            )
            rows += 1
            if len(chunk) >= 50_000:
                fh.write("".join(chunk))
                chunk.clear()
        fh.write("".join(chunk))
    return "price_observation", rows


def gen_review_item(scale: int) -> tuple[str, int]:
    """One review item per ten extracted rows (DB requirement profile)."""

    profile = config.PROFILES[scale]
    path = out_dir(scale) / "review_item.tsv"
    per_day = 500 * scale
    slots = 4 * scale
    rows = 0
    with _writer(path) as fh:
        chunk = []
        for i in range(profile.review_item):
            record_index = i * 10  # every tenth extracted row
            run_index = record_index // RECORDS_PER_RUN
            day, offset = divmod(run_index, per_day)
            slot = offset % slots
            ingest_run_id = day * slots + slot + 1
            created = BASE_DAY + timedelta(days=day, hours=6, seconds=offset % 3600)
            hv = h(i + 77)
            if hv % 10 < 3:
                reason = "identity_ambiguous"
                state = "decided"
                attempt = str(2 * record_index + 2)
                record_ref = "\\N"
                decided = ts(created + timedelta(hours=5))
                decided_by = "owner"
                decision = "confirmed_primary_match"
            else:
                reason = REVIEW_REASONS_PENDING[hv % len(REVIEW_REASONS_PENDING)]
                state = "pending"
                attempt = "\\N"
                record_ref = str(record_index + 1)
                decided = "\\N"
                decided_by = "\\N"
                decision = "\\N"
            chunk.append(
                f"{i + 1}\t{ingest_run_id}\t{run_index + 1}\t{record_ref}\t{attempt}\t{reason}\t"
                f"{state}\t{hv % 5 + 1}\t{ts(created)}\t{decided}\t{decided_by}\t{decision}\t0\n"
            )
            rows += 1
            if len(chunk) >= 50_000:
                fh.write("".join(chunk))
                chunk.clear()
        fh.write("".join(chunk))
    return "review_item", rows


GENERATORS = {
    "card_identity": gen_card_identity,
    "ingest_run": gen_ingest_run,
    "raw_artifact": gen_raw_artifact,
    "processing_run": gen_processing_run,
    "extracted_record": gen_extracted_record,
    "observation_candidate": gen_observation_candidate,
    "identity_resolution_attempt": gen_identity_resolution_attempt,
    "price_observation": gen_price_observation,
    "review_item": gen_review_item,
}


def _run_one(args: tuple[str, int]) -> tuple[str, int]:
    name, scale = args
    return GENERATORS[name](scale)


def generate(scale: int, workers: int | None = None) -> dict[str, int]:
    config.ensure_dirs()
    jobs = [(name, scale) for name in GENERATORS]
    with mp.Pool(processes=workers or min(len(jobs), os.cpu_count() or 4)) as pool:
        results = pool.map(_run_one, jobs)
    return dict(results)


def generate_artifacts(scale: int) -> int:
    """Write the artifact files that raw_artifact rows point at.

    Backup verification checks that every artifact referenced by the restored
    database still exists, so the files must be real.
    """

    profile = config.PROFILES[scale]
    root = config.ARTIFACT_DIR / f"scale{scale}"
    written = 0
    for i in range(profile.raw_artifact):
        shard = root / f"{i % 256:02x}"
        if i % 256 == 0 or not shard.exists():
            shard.mkdir(parents=True, exist_ok=True)
        target = shard / f"{i}.json"
        if not target.exists():
            target.write_text(
                json.dumps({"artifact": i, "rows": RECORDS_PER_RUN, "note": "poc placeholder"}),
                encoding="utf-8",
            )
        written += 1
    history = root / "hi"
    history.mkdir(parents=True, exist_ok=True)
    for index in range(profile.history_days * profile.history_shops):
        target = history / f"{index}.json"
        if not target.exists():
            target.write_text(json.dumps({"artifact": f"history-{index}"}), encoding="utf-8")
        written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", type=int, choices=[1, 10], required=True)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--artifacts", action="store_true", help="also write artifact files")
    args = parser.parse_args()

    with timer() as generation:
        counts = generate(args.scale, args.workers)
    artifact_count = 0
    artifact_seconds = 0.0
    if args.artifacts:
        with timer() as artifacts:
            artifact_count = generate_artifacts(args.scale)
        artifact_seconds = artifacts["seconds"]

    sizes = {
        name: (out_dir(args.scale) / f"{name}.tsv").stat().st_size for name in counts
    }
    result = Result(step="generate", engine="common", scale=args.scale, data={
        "rows": counts,
        "total_rows": sum(counts.values()),
        "file_bytes": sizes,
        "total_file_bytes": sum(sizes.values()),
        "generation_seconds": generation["seconds"],
        "artifact_files": artifact_count,
        "artifact_seconds": artifact_seconds,
    })
    print(json.dumps({"rows": counts, "total_rows": sum(counts.values()),
                      "seconds": round(generation["seconds"], 1),
                      "bytes": sum(sizes.values())}, indent=2))
    print(f"wrote {result.write()}")


if __name__ == "__main__":
    main()
