"""Device token registry foundation.

Revision ID: 0039_device_tokens_foundation
Revises: 0038_notification_events_foundation
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0039_device_tokens_foundation"
down_revision = "0038_notification_events_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("token_preview", sa.String(length=32), nullable=False),
        sa.Column("device_label", sa.String(length=128), nullable=True),
        sa.Column("app_version", sa.String(length=64), nullable=True),
        sa.Column("device_model", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "actor_type",
            "actor_id",
            "provider",
            "platform",
            "token_hash",
            name="uq_device_tokens_actor_provider_platform_hash",
        ),
    )
    op.create_index("ix_device_tokens_actor_id", "device_tokens", ["actor_id"])
    op.create_index("ix_device_tokens_token_hash", "device_tokens", ["token_hash"])
    op.create_index("ix_device_tokens_status", "device_tokens", ["status"])


def downgrade() -> None:
    op.drop_index("ix_device_tokens_status", table_name="device_tokens")
    op.drop_index("ix_device_tokens_token_hash", table_name="device_tokens")
    op.drop_index("ix_device_tokens_actor_id", table_name="device_tokens")
    op.drop_table("device_tokens")
