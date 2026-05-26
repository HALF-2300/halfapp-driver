"""Driver presence and backend ride dismissal records.

Revision ID: 0003_driver_presence_and_visibility_hide
Revises: 0002_canonical_ride_status_contract
Create Date: 2026-05-18 11:34:00
"""
from __future__ import annotations

from alembic import op

from db_migration_helpers import add_column_if_missing, is_postgresql


revision = "0003_driver_presence_and_visibility_hide"
down_revision = "0002_canonical_ride_status_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if is_postgresql(conn):
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS driver_presence (
                id SERIAL PRIMARY KEY,
                driver_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                requested_state VARCHAR NOT NULL DEFAULT 'offline',
                effective_state VARCHAR NOT NULL DEFAULT 'offline',
                state_changed_at TIMESTAMP NOT NULL,
                heartbeat_at TIMESTAMP,
                stale_reason TEXT,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
    else:
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS driver_presence (
                id INTEGER PRIMARY KEY,
                driver_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                requested_state VARCHAR NOT NULL DEFAULT 'offline',
                effective_state VARCHAR NOT NULL DEFAULT 'offline',
                state_changed_at DATETIME NOT NULL,
                heartbeat_at DATETIME,
                stale_reason TEXT,
                updated_at DATETIME NOT NULL
            )
            """
        )
    conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_driver_presence_id ON driver_presence (id)")
    conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_driver_presence_driver_id ON driver_presence (driver_id)")

    add_column_if_missing(
        conn,
        "ride_visibility",
        "expires_at",
        "expires_at TIMESTAMP" if is_postgresql(conn) else "expires_at DATETIME",
    )
    add_column_if_missing(conn, "ride_visibility", "reason", "reason TEXT")
    add_column_if_missing(conn, "ride_visibility", "correlation_id", "correlation_id VARCHAR")
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_ride_visibility_driver_status_expires ON ride_visibility (driver_id, status, expires_at)"
    )


def downgrade() -> None:
    raise RuntimeError("Downgrading driver presence would remove marketplace truth records.")
