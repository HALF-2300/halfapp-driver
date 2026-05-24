"""Payment execution foundation (HALFAPP_PAYMENTS_EXECUTION_01 Phase 1).

Revision ID: 0017_payment_execution_foundation
Revises: 0016_refresh_tokens_foundation
"""
from __future__ import annotations

from alembic import op

revision = "0017_payment_execution_foundation"
down_revision = "0016_refresh_tokens_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS payment_execution (
            id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL,
            ride_pricing_id INTEGER NOT NULL,
            execution_type TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'usd',
            external_provider TEXT,
            external_id TEXT UNIQUE,
            status TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            is_test INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE,
            FOREIGN KEY (ride_pricing_id) REFERENCES ride_pricing(ride_id) ON DELETE CASCADE
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_payment_execution_ride_id ON payment_execution (ride_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_payment_execution_status ON payment_execution (status)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_payment_execution_ride_type ON payment_execution (ride_id, execution_type)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_payment_execution_ride_type")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_payment_execution_status")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_payment_execution_ride_id")
    conn.exec_driver_sql("DROP TABLE IF EXISTS payment_execution")
