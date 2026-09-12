"""failing multi ddl

Deliberately fails on its third DDL statement so the PoC can observe whether a
partially applied migration is possible and how it is identified and repaired.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("review_item", sa.Column("triage_note", sa.String(64), nullable=True))
    op.create_table(
        "migration_probe",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("label", sa.String(32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
        mysql_row_format="DYNAMIC",
    )
    # A card has many observations, so this unique index always violates.
    op.create_index(
        "ix_observation_card_unique", "price_observation", ["card_identity_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_observation_card_unique", table_name="price_observation")
    op.drop_table("migration_probe")
    op.drop_column("review_item", "triage_note")
