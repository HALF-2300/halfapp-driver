"""Driver documents intake foundation.

Revision ID: 0037_driver_documents_foundation
Revises: 0036_driver_readiness_fields
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0037_driver_documents_foundation"
down_revision = "0036_driver_readiness_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "driver_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("storage_mode", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("driver_id", "category", name="uq_driver_documents_driver_category"),
        sa.CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="ck_driver_documents_size_bytes_nonneg",
        ),
    )
    op.create_index("ix_driver_documents_driver_id", "driver_documents", ["driver_id"])
    op.create_index("ix_driver_documents_category", "driver_documents", ["category"])


def downgrade() -> None:
    op.drop_index("ix_driver_documents_category", table_name="driver_documents")
    op.drop_index("ix_driver_documents_driver_id", table_name="driver_documents")
    op.drop_table("driver_documents")
