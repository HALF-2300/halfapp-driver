"""Payout-to-transfer linkage (HALFAPP_PAYMENTS_EXECUTION_05).

Revision ID: 0023_stripe_payout_transfers
Revises: 0022_stripe_payouts
"""
from __future__ import annotations

from alembic import op

revision = "0023_stripe_payout_transfers"
down_revision = "0022_stripe_payouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS stripe_payout_transfers (
            id INTEGER PRIMARY KEY,
            payout_id TEXT NOT NULL,
            transfer_id TEXT NOT NULL,
            stripe_account_id TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (payout_id, transfer_id)
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_payout_transfer_payout "
        "ON stripe_payout_transfers (payout_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_payout_transfer_transfer "
        "ON stripe_payout_transfers (transfer_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_payout_transfer_account "
        "ON stripe_payout_transfers (stripe_account_id)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_payout_transfer_account")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_payout_transfer_transfer")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_payout_transfer_payout")
    conn.exec_driver_sql("DROP TABLE IF EXISTS stripe_payout_transfers")
