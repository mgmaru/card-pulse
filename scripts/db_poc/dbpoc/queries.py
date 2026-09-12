"""The five representative queries from the DB requirements.

Each query has a PostgreSQL and a MariaDB form with the same result contract.
The forms differ only where the products offer different constructs for the
same operation: ``DISTINCT ON`` and ``percentile_cont`` on PostgreSQL against
``ROW_NUMBER`` and ``MEDIAN`` window functions on MariaDB.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import sqlalchemy as sa

from .generate import BASE_DAY, card_uuid, h

# An observation counts as effective unless its newest correction invalidated or
# superseded it. Corrections are append-only, so this replaces an UPDATE.
EFFECTIVE = (
    "COALESCE((SELECT c.action FROM price_observation_correction c"
    " WHERE c.price_observation_id = po.id ORDER BY c.id DESC LIMIT 1), 'restore') = 'restore'"
)

QRY_01 = {
    "postgres": f"""
        WITH latest AS (
            SELECT DISTINCT ON (po.shop_id)
                   po.shop_id, po.amount_minor, po.observed_at
            FROM price_observation po
            WHERE po.card_identity_id = :card
              AND po.price_type = 'buy'
              AND po.currency = 'JPY'
              AND {EFFECTIVE}
            ORDER BY po.shop_id, po.observed_at DESC, po.id DESC
        )
        SELECT COUNT(*) AS shop_count,
               MAX(amount_minor) AS max_amount,
               MIN(amount_minor) AS min_amount,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY amount_minor) AS median_amount,
               MAX(observed_at) AS freshest_observed_at
        FROM latest
    """,
    "mariadb": f"""
        WITH ranked AS (
            SELECT po.shop_id, po.amount_minor, po.observed_at,
                   ROW_NUMBER() OVER (PARTITION BY po.shop_id
                                      ORDER BY po.observed_at DESC, po.id DESC) AS rn
            FROM price_observation po
            WHERE po.card_identity_id = :card
              AND po.price_type = 'buy'
              AND po.currency = 'JPY'
              AND {EFFECTIVE}
        ),
        latest AS (
            SELECT shop_id, amount_minor, observed_at,
                   MEDIAN(amount_minor) OVER () AS median_amount
            FROM ranked WHERE rn = 1
        )
        SELECT COUNT(*) AS shop_count,
               MAX(amount_minor) AS max_amount,
               MIN(amount_minor) AS min_amount,
               MAX(median_amount) AS median_amount,
               MAX(observed_at) AS freshest_observed_at
        FROM latest
    """,
}

QRY_02 = {
    "postgres": f"""
        WITH latest AS (
            SELECT DISTINCT ON (po.card_identity_id, po.shop_id)
                   po.card_identity_id, po.shop_id, po.amount_minor, po.observed_at
            FROM price_observation po
            WHERE po.card_identity_id IN :cards
              AND po.price_type = 'buy'
              AND {EFFECTIVE}
            ORDER BY po.card_identity_id, po.shop_id, po.observed_at DESC, po.id DESC
        )
        SELECT card_identity_id,
               COUNT(*) AS shop_count,
               MAX(amount_minor) AS max_amount,
               MIN(amount_minor) AS min_amount,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY amount_minor) AS median_amount,
               MAX(observed_at) AS freshest_observed_at
        FROM latest
        GROUP BY card_identity_id
    """,
    "mariadb": f"""
        WITH ranked AS (
            SELECT po.card_identity_id, po.shop_id, po.amount_minor, po.observed_at,
                   ROW_NUMBER() OVER (PARTITION BY po.card_identity_id, po.shop_id
                                      ORDER BY po.observed_at DESC, po.id DESC) AS rn
            FROM price_observation po
            WHERE po.card_identity_id IN :cards
              AND po.price_type = 'buy'
              AND {EFFECTIVE}
        ),
        latest AS (
            SELECT card_identity_id, shop_id, amount_minor, observed_at,
                   MEDIAN(amount_minor) OVER (PARTITION BY card_identity_id) AS median_amount
            FROM ranked WHERE rn = 1
        )
        SELECT card_identity_id,
               COUNT(*) AS shop_count,
               MAX(amount_minor) AS max_amount,
               MIN(amount_minor) AS min_amount,
               MAX(median_amount) AS median_amount,
               MAX(observed_at) AS freshest_observed_at
        FROM latest
        GROUP BY card_identity_id
    """,
}

_HISTORY = f"""
    SELECT po.id, po.shop_id, po.amount_minor, po.currency, po.price_type,
           po.card_condition, po.observed_at
    FROM price_observation po
    WHERE po.card_identity_id = :card
      AND po.observed_at >= :since
      AND {EFFECTIVE}
    ORDER BY po.observed_at DESC, po.id DESC
    LIMIT 1000
"""
QRY_03 = {"postgres": _HISTORY, "mariadb": _HISTORY}

_TRACE = """
    SELECT po.id AS observation_id, po.amount_minor, po.observed_at,
           oc.id AS candidate_id, oc.promotion_rule_version,
           er.id AS extracted_record_id, er.locator, er.value_origin,
           pr.id AS processing_run_id, pr.processor_name, pr.processor_version, pr.attempt_no,
           ra.id AS raw_artifact_id, ra.content_hash, ra.storage_ref, ra.fetched_at,
           ir.id AS ingest_run_id, ir.status, s.slug AS source_slug
    FROM price_observation po
    JOIN observation_candidate oc ON oc.id = po.observation_candidate_id
    JOIN extracted_record er ON er.id = oc.extracted_record_id
    JOIN processing_run pr ON pr.id = er.processing_run_id
    JOIN raw_artifact ra ON ra.id = pr.raw_artifact_id
    JOIN ingest_run ir ON ir.id = ra.ingest_run_id
    JOIN source s ON s.id = ra.source_id
    WHERE po.id = :observation_id
"""
QRY_04 = {"postgres": _TRACE, "mariadb": _TRACE}

_REVIEW = """
    SELECT ri.id, ri.reason, ri.priority, ri.created_at,
           ri.raw_artifact_id, ri.extracted_record_id
    FROM review_item ri
    WHERE ri.state = 'pending'
    ORDER BY ri.priority ASC, ri.created_at ASC, ri.id ASC
    LIMIT 100
"""
QRY_05 = {"postgres": _REVIEW, "mariadb": _REVIEW}

QUERIES = {
    "DB-QRY-01": QRY_01,
    "DB-QRY-02": QRY_02,
    "DB-QRY-03": QRY_03,
    "DB-QRY-04": QRY_04,
    "DB-QRY-05": QRY_05,
}

TARGET_P95_MS = {
    "DB-QRY-01": 200.0,
    "DB-QRY-02": 1000.0,
    "DB-QRY-03": 500.0,
    "DB-QRY-04": 200.0,
    "DB-QRY-05": 200.0,
}

EXPANDING = {"DB-QRY-02": "cards"}


def statement(name: str, engine_name: str) -> sa.TextClause:
    text = sa.text(QUERIES[name][engine_name])
    expanding = EXPANDING.get(name)
    if expanding:
        text = text.bindparams(sa.bindparam(expanding, expanding=True))
    return text


def params_for(name: str, iteration: int, cards: int, observations: int,
               history_cards: int = 200) -> dict:
    """Deterministic but varied parameters, so the cache is not trivially warm."""

    match name:
        case "DB-QRY-01":
            return {"card": card_uuid(h(iteration) % cards)}
        case "DB-QRY-02":
            start = h(iteration) % max(cards - 100, 1)
            return {"cards": [card_uuid((start + i) % cards) for i in range(100)]}
        case "DB-QRY-03":
            since = (BASE_DAY - timedelta(days=365)).replace(tzinfo=None)
            return {"card": card_uuid(h(iteration) % history_cards), "since": since}
        case "DB-QRY-04":
            return {"observation_id": h(iteration) % observations + 1}
        case _:
            return {}
