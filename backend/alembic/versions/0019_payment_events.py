"""Payment webhook event deduplication (HALFAPP_PAYMENTS_EXECUTION_02_5).

Revision ID: 0019_payment_events
Revises: 0018_driver_stripe_accounts
"""
from __future__ import annotations

from alembic import op

revision = "0019_payment_events"
down_revision = "0018_driver_stripe_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS payment_events (
            id INTEGER PRIMARY KEY,
            external_event_id TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            payment_execution_id INTEGER,
            processed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_payment_events_external_event_id "
        "ON payment_events (external_event_id)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_payment_events_external_event_id")
    conn.exec_driver_sql("DROP TABLE IF EXISTS payment_events")
