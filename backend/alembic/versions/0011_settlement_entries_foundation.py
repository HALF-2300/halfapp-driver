"""Settlement entries foundation — immutable obligations from locked ride_pricing.

Revision ID: 0011_settlement_entries_foundation
Revises: 0010_route_snapshots_foundation
Create Date: 2026-05-22 23:00:00
"""
from __future__ import annotations

from alembic import op

revision = "0011_settlement_entries_foundation"
down_revision = "0010_route_snapshots_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS settlement_entries (
            id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL,
            pricing_id INTEGER NOT NULL,
            route_snapshot_id INTEGER,
            settlement_status TEXT NOT NULL DEFAULT 'ready',
            entry_type TEXT NOT NULL,
            party TEXT NOT NULL,
            amount_cents INTEGER NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'USD',
            source TEXT NOT NULL DEFAULT 'ride_pricing_locked',
            entry_checksum TEXT NOT NULL,
            metadata_json TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            locked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE,
            FOREIGN KEY (pricing_id) REFERENCES ride_pricing(ride_id) ON DELETE CASCADE,
            FOREIGN KEY (route_snapshot_id) REFERENCES route_snapshots(id) ON DELETE SET NULL,
            CHECK (settlement_status IN (
                'pending', 'ready', 'manually_marked_paid', 'cancelled', 'disputed_placeholder'
            )),
            CHECK (amount_cents >= 0),
            UNIQUE (ride_id, entry_type)
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_settlement_entries_ride_id ON settlement_entries (ride_id)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP TABLE IF EXISTS settlement_entries")
