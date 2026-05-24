"""Add reason + created_at to ride_dispatch_log when missing (RIDE-003).

Revision ID: 0015_dispatch_log_reason
Revises: 0014_dispatch_cascade
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0015_dispatch_log_reason"
down_revision = "0014_dispatch_cascade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("ride_dispatch_log"):
        return
    columns = {col["name"] for col in inspector.get_columns("ride_dispatch_log")}
    if "reason" not in columns:
        op.add_column("ride_dispatch_log", sa.Column("reason", sa.String(length=255), nullable=True))
    if "created_at" not in columns:
        op.add_column("ride_dispatch_log", sa.Column("created_at", sa.DateTime(), nullable=True))
        op.execute("UPDATE ride_dispatch_log SET created_at = sent_at WHERE created_at IS NULL")
        with op.batch_alter_table("ride_dispatch_log") as batch_op:
            batch_op.alter_column("created_at", nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("ride_dispatch_log"):
        return
    columns = {col["name"] for col in inspector.get_columns("ride_dispatch_log")}
    if "created_at" in columns:
        op.drop_column("ride_dispatch_log", "created_at")
    if "reason" in columns:
        op.drop_column("ride_dispatch_log", "reason")
