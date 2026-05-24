"""Ride messages + driver support tickets (gap-fill).

Revision ID: 0028_ride_messages_support_tickets
Revises: 0027_password_reset_tokens
"""
from __future__ import annotations

from alembic import op

revision = "0028_ride_messages_support_tickets"
down_revision = "0027_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS ride_messages (
            id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL,
            sender_role VARCHAR(16) NOT NULL,
            sender_id INTEGER,
            body TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            read_by_driver_at DATETIME,
            FOREIGN KEY(ride_id) REFERENCES rides(id) ON DELETE CASCADE
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_ride_messages_ride_id ON ride_messages (ride_id)"
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS driver_support_tickets (
            id INTEGER PRIMARY KEY,
            ride_id INTEGER,
            driver_id INTEGER NOT NULL,
            category VARCHAR(64) NOT NULL DEFAULT 'trip_issue',
            message TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(ride_id) REFERENCES rides(id) ON DELETE SET NULL,
            FOREIGN KEY(driver_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_driver_support_tickets_driver_id ON driver_support_tickets (driver_id)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP TABLE IF EXISTS driver_support_tickets")
    conn.exec_driver_sql("DROP TABLE IF EXISTS ride_messages")
