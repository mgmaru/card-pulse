"""backward compatible change

Adds a nullable column, a new index on a large table, and a new table. Used to
measure how long each candidate blocks readers and writers during a change that
old queries can survive.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

import dbpoc.schema

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TS = dbpoc.schema.TS


def upgrade() -> None:
    op.add_column("price_observation", sa.Column("freshness_note", sa.String(120), nullable=True))
    op.create_index(
        "ix_observation_shop_observed", "price_observation", ["shop_id", "observed_at"]
    )
    op.create_table(
        "price_alert_rule",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("card_identity_id", dbpoc.schema.NativeUuid(), nullable=False),
        sa.Column("threshold_minor", sa.BigInteger(), nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["card_identity_id"], ["card_identity.id"]),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
        mysql_row_format="DYNAMIC",
    )


def downgrade() -> None:
    op.drop_table("price_alert_rule")
    op.drop_index("ix_observation_shop_observed", table_name="price_observation")
    op.drop_column("price_observation", "freshness_note")
