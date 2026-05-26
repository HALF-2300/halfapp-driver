"""Revision ID: 0032_ride_payments_foundation

Phase 3 product payment rows (simulated money loop).
"""
from __future__ import annotations

from alembic import op

revision = "0032_ride_payments_foundation"
down_revision = "0031_crl_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS ride_payments (
            id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL UNIQUE REFERENCES rides(id) ON DELETE CASCADE,
            rider_id INTEGER REFERENCES users(id),
            driver_id INTEGER REFERENCES users(id),
            amount_cents INTEGER NOT NULL DEFAULT 0,
            driver_payout_cents INTEGER NOT NULL DEFAULT 0,
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            authorized_at DATETIME,
            captured_at DATETIME,
            failed_at DATETIME,
            CHECK (status IN ('pending', 'authorized', 'captured', 'failed'))
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_ride_payments_rider_id ON ride_payments (rider_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_ride_payments_driver_id ON ride_payments (driver_id)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP TABLE IF EXISTS ride_payments")
