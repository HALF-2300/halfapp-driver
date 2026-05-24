"""Driver Stripe Connect accounts (HALFAPP_PAYMENTS_EXECUTION_02).

Revision ID: 0018_driver_stripe_accounts
Revises: 0017_payment_execution_foundation
"""
from __future__ import annotations

from alembic import op

revision = "0018_driver_stripe_accounts"
down_revision = "0017_payment_execution_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS driver_stripe_accounts (
            id INTEGER PRIMARY KEY,
            driver_id INTEGER NOT NULL UNIQUE,
            stripe_account_id TEXT NOT NULL UNIQUE,
            charges_enabled INTEGER NOT NULL DEFAULT 0,
            payouts_enabled INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_driver_stripe_accounts_driver_id ON driver_stripe_accounts (driver_id)"
    )
    conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_driver_stripe_accounts_stripe_account_id "
        "ON driver_stripe_accounts (stripe_account_id)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_driver_stripe_accounts_stripe_account_id")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_driver_stripe_accounts_driver_id")
    conn.exec_driver_sql("DROP TABLE IF EXISTS driver_stripe_accounts")
