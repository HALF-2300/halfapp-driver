"""Driver online/offline status with location freshness (DRIVER-001).

Revision ID: 0013_driver_status_online_offline
Revises: 0012_driver_approvals_foundation
Create Date: 2026-05-22 12:00:00
"""
from __future__ import annotations

from alembic import op

revision = "0013_driver_status_online_offline"
down_revision = "0012_driver_approvals_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS driver_status (
            id INTEGER PRIMARY KEY,
            driver_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            online INTEGER NOT NULL DEFAULT 0,
            last_lat REAL,
            last_lng REAL,
            last_seen_at DATETIME,
            current_ride_id INTEGER REFERENCES rides(id),
            updated_at DATETIME NOT NULL
        )
        """
    )
    conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_driver_status_id ON driver_status (id)")
    conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_driver_status_driver_id ON driver_status (driver_id)"
    )


def downgrade() -> None:
    raise RuntimeError("Downgrading driver_status would remove DRIVER-001 marketplace truth.")
