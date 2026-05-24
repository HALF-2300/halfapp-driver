"""Payment execution charge id for transfer linkage (HALFAPP_PAYMENTS_EXECUTION_05).

Revision ID: 0020_payment_execution_charge_id
Revises: 0019_payment_events
"""
from __future__ import annotations

from alembic import op

revision = "0020_payment_execution_charge_id"
down_revision = "0019_payment_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        "ALTER TABLE payment_execution ADD COLUMN external_charge_id TEXT"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_payment_execution_external_charge_id "
        "ON payment_execution (external_charge_id)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_payment_execution_external_charge_id")
    conn.exec_driver_sql("ALTER TABLE payment_execution DROP COLUMN external_charge_id")
