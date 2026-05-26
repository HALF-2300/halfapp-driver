"""Driver readiness operator fields.

Revision ID: 0036_driver_readiness_fields
Revises: 0035_telemetry_retention_index
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0036_driver_readiness_fields"
down_revision = "0035_telemetry_retention_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "insurance_expires_at" not in columns:
        op.add_column("users", sa.Column("insurance_expires_at", sa.DateTime(timezone=True), nullable=True))
    if "vehicle_ready" not in columns:
        op.add_column("users", sa.Column("vehicle_ready", sa.Boolean(), nullable=True))
        if dialect == "postgresql":
            conn.exec_driver_sql("UPDATE users SET vehicle_ready = false WHERE vehicle_ready IS NULL")
            conn.exec_driver_sql("ALTER TABLE users ALTER COLUMN vehicle_ready SET DEFAULT false")
            conn.exec_driver_sql("ALTER TABLE users ALTER COLUMN vehicle_ready SET NOT NULL")
        else:
            conn.exec_driver_sql("UPDATE users SET vehicle_ready = 0 WHERE vehicle_ready IS NULL")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "vehicle_ready" in columns:
        op.drop_column("users", "vehicle_ready")
    if "insurance_expires_at" in columns:
        op.drop_column("users", "insurance_expires_at")
