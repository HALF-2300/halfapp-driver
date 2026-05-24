"""Restore metadata-backed schema indexes.

Revision ID: 0004_restore_schema_indexes
Revises: 0003_driver_presence_and_visibility_hide
Create Date: 2026-05-18 11:58:30
"""
from __future__ import annotations

from alembic import op


revision = "0004_restore_schema_indexes"
down_revision = "0003_driver_presence_and_visibility_hide"
branch_labels = None
depends_on = None


INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS ix_events_entity ON events (entity_type, entity_id)",
    "CREATE INDEX IF NOT EXISTS ix_events_occurred_at ON events (occurred_at)",
    "CREATE INDEX IF NOT EXISTS ix_metrics_driver_id ON metrics (driver_id)",
    "CREATE INDEX IF NOT EXISTS ix_metrics_id ON metrics (id)",
    "CREATE INDEX IF NOT EXISTS ix_metrics_metric_name ON metrics (metric_name)",
    "CREATE INDEX IF NOT EXISTS ix_metrics_ride_id ON metrics (ride_id)",
    "CREATE INDEX IF NOT EXISTS ix_notifications_id ON notifications (id)",
    "CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_ride_claim_attempts_driver_id ON ride_claim_attempts (driver_id)",
    "CREATE INDEX IF NOT EXISTS ix_ride_claim_attempts_ride_id ON ride_claim_attempts (ride_id)",
    "CREATE INDEX IF NOT EXISTS ix_ride_visibility_driver_dismissed ON ride_visibility (driver_id, dismissed_at)",
    "CREATE INDEX IF NOT EXISTS ix_ride_visibility_driver_status_expires ON ride_visibility (driver_id, status, expires_at)",
    "CREATE INDEX IF NOT EXISTS ix_ride_visibility_ride_id ON ride_visibility (ride_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_ride_visibility_ride_driver ON ride_visibility (ride_id, driver_id)",
    "CREATE INDEX IF NOT EXISTS ix_rides_created_at ON rides (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_rides_customer_id ON rides (customer_id)",
    "CREATE INDEX IF NOT EXISTS ix_rides_driver_id ON rides (driver_id)",
    "CREATE INDEX IF NOT EXISTS ix_rides_id ON rides (id)",
    "CREATE INDEX IF NOT EXISTS ix_rides_status_driver_id ON rides (status, driver_id)",
    "CREATE INDEX IF NOT EXISTS ix_users_availability ON users (availability)",
    "CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)",
    "CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)",
)


def upgrade() -> None:
    conn = op.get_bind()
    for statement in INDEX_STATEMENTS:
        conn.exec_driver_sql(statement)


def downgrade() -> None:
    raise RuntimeError("Downgrading restored schema indexes is not supported.")
