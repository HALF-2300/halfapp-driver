"""Ensure driver telemetry ``created_at`` is indexed for retention deletes.

Revision ID: 0035_telemetry_retention_index
Revises: 0034_sil_crl_snapshots
"""
from __future__ import annotations

from alembic import op

revision = "0035_telemetry_retention_index"
down_revision = "0034_sil_crl_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_driver_telemetry_created_at "
        "ON driver_telemetry_points (created_at)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_driver_telemetry_created_at")
