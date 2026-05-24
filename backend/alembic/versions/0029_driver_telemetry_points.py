"""Fleet telemetry points for keyless traffic heat overlay.

Revision ID: 0029_driver_telemetry_points
Revises: 0028_ride_messages_support_tickets
"""
from __future__ import annotations

from alembic import op

revision = "0029_driver_telemetry_points"
down_revision = "0028_ride_messages_support_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS driver_telemetry_points (
            id INTEGER PRIMARY KEY,
            driver_id INTEGER NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            speed_mps REAL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(driver_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_driver_telemetry_driver_id ON driver_telemetry_points (driver_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_driver_telemetry_created_at ON driver_telemetry_points (created_at)"
    )


def downgrade() -> None:
    op.drop_table("driver_telemetry_points")
