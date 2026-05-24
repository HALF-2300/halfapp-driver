"""Stripe Connect account payouts (HALFAPP_PAYMENTS_EXECUTION_05).

Revision ID: 0022_stripe_payouts
Revises: 0021_stripe_transfers
"""
from __future__ import annotations

from alembic import op

revision = "0022_stripe_payouts"
down_revision = "0021_stripe_transfers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS stripe_payouts (
            id INTEGER PRIMARY KEY,
            payout_id TEXT NOT NULL UNIQUE,
            stripe_account_id TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL,
            status TEXT NOT NULL,
            arrival_date DATETIME,
            created_at DATETIME,
            ingested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_stripe_payouts_payout_id "
        "ON stripe_payouts (payout_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_stripe_payouts_account "
        "ON stripe_payouts (stripe_account_id)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_stripe_payouts_account")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_stripe_payouts_payout_id")
    conn.exec_driver_sql("DROP TABLE IF EXISTS stripe_payouts")
