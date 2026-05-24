"""Driver profile preferences (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02).

Revision ID: 0024_driver_profiles
Revises: 0023_stripe_payout_transfers
"""
from __future__ import annotations

from alembic import op

revision = "0024_driver_profiles"
down_revision = "0023_stripe_payout_transfers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS driver_profiles (
            driver_id INTEGER PRIMARY KEY,
            display_name TEXT,
            phone_e164 TEXT,
            photo_url TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_driver_profiles_phone "
        "ON driver_profiles (phone_e164)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_driver_profiles_phone")
    conn.exec_driver_sql("DROP TABLE IF EXISTS driver_profiles")
