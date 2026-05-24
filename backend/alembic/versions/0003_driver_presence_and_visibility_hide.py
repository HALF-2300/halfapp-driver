"""Driver presence and backend ride dismissal records.

Revision ID: 0003_driver_presence_and_visibility_hide
Revises: 0002_canonical_ride_status_contract
Create Date: 2026-05-18 11:34:00
"""
from __future__ import annotations

from alembic import op


revision = "0003_driver_presence_and_visibility_hide"
down_revision = "0002_canonical_ride_status_contract"
branch_labels = None
depends_on = None


def _columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}


def _add_column_if_missing(conn, table: str, column: str, ddl: str) -> None:
    if column not in _columns(conn, table):
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def upgrade() -> None:
    conn = op.get_bind()
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

    _add_column_if_missing(conn, "ride_visibility", "expires_at", "expires_at DATETIME")
    _add_column_if_missing(conn, "ride_visibility", "reason", "reason TEXT")
    _add_column_if_missing(conn, "ride_visibility", "correlation_id", "correlation_id VARCHAR")
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_ride_visibility_driver_status_expires ON ride_visibility (driver_id, status, expires_at)"
    )


def downgrade() -> None:
    raise RuntimeError("Downgrading driver presence would remove marketplace truth records.")
