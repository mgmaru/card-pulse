"""PoC schema.

This schema is a PoC subset of docs/architecture/data-model.md. It exists to
compare database products under the same structure, not to fix the MVP data
model. CP-0016 finalizes the real model and CP-0019/CP-0020 decide the real
idempotency keys and transaction boundaries.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.types import UserDefinedType


class NativeUuid(UserDefinedType):
    """``UUID`` column type on both candidates.

    PostgreSQL has had a native ``uuid`` type for a long time and MariaDB has
    one since 10.7, so the same DDL works on both. SQLAlchemy's generic
    ``sa.Uuid`` falls back to ``CHAR(32)`` on MariaDB, which would compare a
    16-byte native type against a 32-character string column and invalidate the
    comparison.
    """

    cache_ok = True

    def get_col_spec(self, **kw: object) -> str:
        return "UUID"

    def bind_processor(self, dialect):  # noqa: ANN001, ANN201
        def process(value):  # noqa: ANN001, ANN202
            return str(value) if value is not None else None

        return process

    def result_processor(self, dialect, coltype):  # noqa: ANN001, ANN201
        def process(value):  # noqa: ANN001, ANN202
            return str(value) if value is not None else None

        return process


UUID = NativeUuid()

TS = sa.DateTime(timezone=True).with_variant(mysql.DATETIME(fsp=6), "mysql", "mariadb")
JSONB = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
SCORE = sa.Numeric(5, 4)

TABLE_KW = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_row_format": "DYNAMIC"}

# Tables in dependency order; also the load and count-verification order.
TABLE_ORDER = (
    "source",
    "shop",
    "card_identity",
    "card_external_reference",
    "ingest_run",
    "raw_artifact",
    "processing_run",
    "extracted_record",
    "observation_candidate",
    "identity_resolution_attempt",
    "price_observation",
    "price_observation_correction",
    "review_item",
)

# Tables produced by the bulk generator, in load order.
BULK_TABLES = (
    "card_identity",
    "ingest_run",
    "raw_artifact",
    "processing_run",
    "extracted_record",
    "observation_candidate",
    "identity_resolution_attempt",
    "price_observation",
    "review_item",
)


def build_metadata() -> sa.MetaData:
    metadata = sa.MetaData()

    sa.Table(
        "source",
        metadata,
        sa.Column("id", sa.SmallInteger, primary_key=True, autoincrement=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("stopped_reason", sa.String(200)),
        sa.Column("last_success_run_id", sa.BigInteger),
        sa.CheckConstraint("state IN ('active','paused','stopped')", name="ck_source_state"),
        **TABLE_KW,
    )

    sa.Table(
        "shop",
        metadata,
        sa.Column("id", sa.SmallInteger, primary_key=True, autoincrement=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("normalized_name", sa.String(120), nullable=False),
        **TABLE_KW,
    )

    sa.Table(
        "card_identity",
        metadata,
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tcg", sa.String(32), nullable=False),
        sa.Column("set_code", sa.String(32), nullable=False),
        sa.Column("card_number", sa.String(32), nullable=False),
        sa.Column("rarity", sa.String(32), nullable=False),
        sa.Column("edition", sa.String(32), nullable=False),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("normalized_name", sa.String(200), nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.UniqueConstraint(
            "tcg", "set_code", "card_number", "rarity", "edition", "language",
            name="uq_card_identity_attributes",
        ),
        sa.Index("ix_card_identity_normalized_name", "normalized_name"),
        **TABLE_KW,
    )

    sa.Table(
        "card_external_reference",
        metadata,
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("card_identity_id", UUID, sa.ForeignKey("card_identity.id"), nullable=False),
        sa.Column("namespace", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("evidence", sa.String(120), nullable=False),
        sa.Column("confirmed", sa.Boolean, nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.UniqueConstraint("namespace", "external_id", name="uq_card_external_reference"),
        **TABLE_KW,
    )

    sa.Table(
        "ingest_run",
        metadata,
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("source_id", sa.SmallInteger, sa.ForeignKey("source.id"), nullable=False),
        sa.Column("started_at", TS, nullable=False),
        sa.Column("finished_at", TS),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("fetched_count", sa.Integer, nullable=False),
        sa.Column("parsed_count", sa.Integer, nullable=False),
        sa.Column("stored_count", sa.Integer, nullable=False),
        sa.Column("error_class", sa.String(40)),
        sa.CheckConstraint(
            "status IN ('succeeded','partial','failed','empty','running')",
            name="ck_ingest_run_status",
        ),
        sa.Index("ix_ingest_run_source_started", "source_id", "started_at"),
        **TABLE_KW,
    )

    sa.Table(
        "raw_artifact",
        metadata,
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("ingest_run_id", sa.BigInteger, sa.ForeignKey("ingest_run.id"), nullable=False),
        sa.Column("source_id", sa.SmallInteger, sa.ForeignKey("source.id"), nullable=False),
        sa.Column("source_item_id", sa.String(128), nullable=False),
        sa.Column("url", sa.String(500)),
        sa.Column("mime_type", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        sa.Column("byte_size", sa.BigInteger, nullable=False),
        sa.Column("fetched_at", TS, nullable=False),
        sa.Column("published_at", TS),
        sa.Column("storage_ref", sa.String(300), nullable=False),
        sa.UniqueConstraint("source_id", "content_hash", name="uq_raw_artifact_source_hash"),
        sa.CheckConstraint("byte_size >= 0", name="ck_raw_artifact_byte_size"),
        sa.Index("ix_raw_artifact_fetched_at", "fetched_at"),
        **TABLE_KW,
    )

    sa.Table(
        "processing_run",
        metadata,
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("raw_artifact_id", sa.BigInteger, sa.ForeignKey("raw_artifact.id"), nullable=False),
        sa.Column("processor_name", sa.String(64), nullable=False),
        sa.Column("processor_version", sa.String(32), nullable=False),
        sa.Column("config_ref", sa.String(64), nullable=False),
        sa.Column("attempt_no", sa.SmallInteger, nullable=False),
        sa.Column("started_at", TS, nullable=False),
        sa.Column("finished_at", TS),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("extracted_count", sa.Integer, nullable=False),
        sa.Column("promoted_count", sa.Integer, nullable=False),
        sa.Column("error_class", sa.String(40)),
        sa.UniqueConstraint(
            "raw_artifact_id", "processor_name", "processor_version", "config_ref", "attempt_no",
            name="uq_processing_run_reparse",
        ),
        **TABLE_KW,
    )

    sa.Table(
        "extracted_record",
        metadata,
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("processing_run_id", sa.BigInteger, sa.ForeignKey("processing_run.id"), nullable=False),
        sa.Column("raw_artifact_id", sa.BigInteger, sa.ForeignKey("raw_artifact.id"), nullable=False),
        sa.Column("locator", sa.String(160), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("value_origin", sa.String(32), nullable=False),
        sa.Column("confidence", SCORE),
        sa.Column("warnings", sa.String(200)),
        sa.Column("created_at", TS, nullable=False),
        sa.Index("ix_extracted_record_processing_run", "processing_run_id"),
        sa.Index("ix_extracted_record_artifact", "raw_artifact_id"),
        **TABLE_KW,
    )

    sa.Table(
        "observation_candidate",
        metadata,
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("extracted_record_id", sa.BigInteger, sa.ForeignKey("extracted_record.id"), nullable=False),
        sa.Column("shop_id", sa.SmallInteger, sa.ForeignKey("shop.id"), nullable=False),
        sa.Column("source_id", sa.SmallInteger, sa.ForeignKey("source.id"), nullable=False),
        sa.Column("tcg", sa.String(32), nullable=False),
        sa.Column("amount_minor", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("price_type", sa.String(16), nullable=False),
        sa.Column("raw_card_name", sa.String(200), nullable=False),
        sa.Column("raw_card_number", sa.String(32)),
        sa.Column("raw_set", sa.String(32)),
        sa.Column("raw_rarity", sa.String(32)),
        sa.Column("raw_edition", sa.String(32)),
        sa.Column("raw_language", sa.String(8)),
        sa.Column("raw_condition", sa.String(16)),
        sa.Column("observed_at", TS, nullable=False),
        sa.Column("promotion_rule_version", sa.String(16), nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.UniqueConstraint(
            "extracted_record_id", "promotion_rule_version", name="uq_candidate_record_rule"
        ),
        sa.CheckConstraint("amount_minor >= 0", name="ck_candidate_amount_non_negative"),
        sa.CheckConstraint("price_type IN ('buy','sell')", name="ck_candidate_price_type"),
        **TABLE_KW,
    )

    sa.Table(
        "identity_resolution_attempt",
        metadata,
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column(
            "observation_candidate_id",
            sa.BigInteger,
            sa.ForeignKey("observation_candidate.id"),
            nullable=False,
        ),
        sa.Column("matcher_name", sa.String(64), nullable=False),
        sa.Column("matcher_version", sa.String(32), nullable=False),
        sa.Column("card_identity_id", UUID, sa.ForeignKey("card_identity.id")),
        sa.Column("match_score", SCORE, nullable=False),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("evidence", sa.String(120), nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.CheckConstraint(
            "result IN ('confirmed','rejected','ambiguous')", name="ck_attempt_result"
        ),
        sa.CheckConstraint("match_score >= 0 AND match_score <= 1", name="ck_attempt_score_range"),
        sa.Index("ix_attempt_candidate", "observation_candidate_id"),
        **TABLE_KW,
    )

    sa.Table(
        "price_observation",
        metadata,
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column(
            "observation_candidate_id",
            sa.BigInteger,
            sa.ForeignKey("observation_candidate.id"),
            nullable=False,
        ),
        sa.Column("card_identity_id", UUID, sa.ForeignKey("card_identity.id"), nullable=False),
        sa.Column("shop_id", sa.SmallInteger, sa.ForeignKey("shop.id"), nullable=False),
        sa.Column("source_id", sa.SmallInteger, sa.ForeignKey("source.id"), nullable=False),
        sa.Column("raw_artifact_id", sa.BigInteger, sa.ForeignKey("raw_artifact.id"), nullable=False),
        sa.Column("tcg", sa.String(32), nullable=False),
        sa.Column("amount_minor", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("price_type", sa.String(16), nullable=False),
        sa.Column("card_condition", sa.String(16), nullable=False),
        sa.Column("observed_at", TS, nullable=False),
        sa.Column("collected_at", TS, nullable=False),
        sa.Column("published_at", TS),
        sa.Column("valid_until", TS),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_price_observation_idempotency"),
        sa.CheckConstraint("amount_minor >= 0", name="ck_observation_amount_non_negative"),
        sa.CheckConstraint("price_type IN ('buy','sell')", name="ck_observation_price_type"),
        sa.Index("ix_observation_card_observed", "card_identity_id", "observed_at"),
        sa.Index(
            "ix_observation_card_shop_observed", "card_identity_id", "shop_id", "observed_at"
        ),
        sa.Index("ix_observation_candidate", "observation_candidate_id"),
        sa.Index("ix_observation_collected_at", "collected_at"),
        **TABLE_KW,
    )

    sa.Table(
        "price_observation_correction",
        metadata,
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "price_observation_id",
            sa.BigInteger,
            sa.ForeignKey("price_observation.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("replacement_id", sa.BigInteger, sa.ForeignKey("price_observation.id")),
        sa.Column("created_at", TS, nullable=False),
        sa.CheckConstraint(
            "action IN ('invalidate','supersede','restore')", name="ck_correction_action"
        ),
        sa.Index("ix_correction_observation", "price_observation_id", "id"),
        **TABLE_KW,
    )

    sa.Table(
        "review_item",
        metadata,
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("ingest_run_id", sa.BigInteger, sa.ForeignKey("ingest_run.id"), nullable=False),
        sa.Column("raw_artifact_id", sa.BigInteger, sa.ForeignKey("raw_artifact.id"), nullable=False),
        sa.Column("extracted_record_id", sa.BigInteger, sa.ForeignKey("extracted_record.id")),
        sa.Column(
            "identity_resolution_attempt_id",
            sa.BigInteger,
            sa.ForeignKey("identity_resolution_attempt.id"),
        ),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("priority", sa.SmallInteger, nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("decided_at", TS),
        sa.Column("decided_by", sa.String(64)),
        sa.Column("decision", sa.String(32)),
        sa.Column("lock_version", sa.Integer, nullable=False),
        sa.CheckConstraint("state IN ('pending','decided','dismissed')", name="ck_review_state"),
        sa.Index("ix_review_state_priority", "state", "priority", "created_at"),
        **TABLE_KW,
    )

    return metadata


METADATA = build_metadata()
