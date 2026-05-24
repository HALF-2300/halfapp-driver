"""Stripe Connect transfers (HALFAPP_PAYMENTS_EXECUTION_05).

Revision ID: 0021_stripe_transfers
Revises: 0020_payment_execution_charge_id
"""
from __future__ import annotations

from alembic import op

revision = "0021_stripe_transfers"
down_revision = "0020_payment_execution_charge_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS stripe_transfers (
            id INTEGER PRIMARY KEY,
            transfer_id TEXT NOT NULL UNIQUE,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL,
            destination_account_id TEXT,
            source_transaction TEXT,
            reversed INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME,
            payment_execution_id INTEGER,
            ingested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_stripe_transfers_transfer_id "
        "ON stripe_transfers (transfer_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_stripe_transfers_dest "
        "ON stripe_transfers (destination_account_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_stripe_transfers_exec "
        "ON stripe_transfers (payment_execution_id)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_stripe_transfers_exec")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_stripe_transfers_dest")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_stripe_transfers_transfer_id")
    conn.exec_driver_sql("DROP TABLE IF EXISTS stripe_transfers")
