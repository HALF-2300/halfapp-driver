"""SIL/CRL worker snapshot indexes (tables from 0030/0031).

Revision ID: 0034_sil_crl_snapshots
Revises: 0032_ride_payments_foundation
"""
from __future__ import annotations

from alembic import op

revision = "0034_sil_crl_snapshots"
down_revision = "0032_ride_payments_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # sil_cell_aggregate + crl_cell_snapshot + crl_cell_explanation created in 0030/0031.
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_sil_cell_aggregate_computed_at "
        "ON sil_cell_aggregate (computed_at)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_crl_cell_snapshot_computed_at "
        "ON crl_cell_snapshot (computed_at)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_crl_cell_explanation_computed_at "
        "ON crl_cell_explanation (computed_at)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_crl_cell_explanation_computed_at")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_crl_cell_snapshot_computed_at")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_sil_cell_aggregate_computed_at")
