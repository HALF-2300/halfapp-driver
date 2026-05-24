"""RIDE-003 dispatch cascade columns + no_drivers_available status + dispatch log.

Revision ID: 0014_dispatch_cascade
Revises: 0013_driver_status_online_offline
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014_dispatch_cascade"
down_revision = "0013_driver_status_online_offline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ride_dispatch_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ride_id", sa.Integer(), sa.ForeignKey("rides.id", ondelete="CASCADE"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ride_dispatch_log_ride_id", "ride_dispatch_log", ["ride_id"])
    op.create_index("ix_ride_dispatch_log_driver_id", "ride_dispatch_log", ["driver_id"])

    with op.batch_alter_table("rides") as batch_op:
        batch_op.add_column(sa.Column("dispatch_driver_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("dispatch_expires_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("dispatch_attempt_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("rides") as batch_op:
        batch_op.drop_column("dispatch_attempt_count")
        batch_op.drop_column("dispatch_expires_at")
        batch_op.drop_column("dispatch_driver_id")
    op.drop_index("ix_ride_dispatch_log_driver_id", table_name="ride_dispatch_log")
    op.drop_index("ix_ride_dispatch_log_ride_id", table_name="ride_dispatch_log")
    op.drop_table("ride_dispatch_log")
