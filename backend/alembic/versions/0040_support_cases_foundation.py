"""Support cases foundation (HALFAPP_SUPPORT_HELP_LOST_ITEM_CONTRACT_01).

Revision ID: 0040_support_cases_foundation
Revises: 0039_device_tokens_foundation
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0040_support_cases_foundation"
down_revision = "0039_device_tokens_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_uid", sa.String(length=32), nullable=False),
        sa.Column("ride_id", sa.Integer(), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("contact_preference", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ride_id"], ["rides.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_uid", name="uq_support_cases_case_uid"),
    )
    op.create_index("ix_support_cases_ride_id", "support_cases", ["ride_id"])
    op.create_index("ix_support_cases_actor_type", "support_cases", ["actor_type"])
    op.create_index("ix_support_cases_actor_id", "support_cases", ["actor_id"])
    op.create_index("ix_support_cases_category", "support_cases", ["category"])
    op.create_index("ix_support_cases_status", "support_cases", ["status"])


def downgrade() -> None:
    op.drop_index("ix_support_cases_status", table_name="support_cases")
    op.drop_index("ix_support_cases_category", table_name="support_cases")
    op.drop_index("ix_support_cases_actor_id", table_name="support_cases")
    op.drop_index("ix_support_cases_actor_type", table_name="support_cases")
    op.drop_index("ix_support_cases_ride_id", table_name="support_cases")
    op.drop_table("support_cases")
