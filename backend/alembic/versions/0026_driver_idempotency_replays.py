"""Driver ride-write idempotency replays (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_03).

Revision ID: 0026_driver_idempotency_replays
Revises: 0025_driver_settings
"""
from __future__ import annotations

from alembic import op

revision = "0026_driver_idempotency_replays"
down_revision = "0025_driver_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS driver_idempotency_replays (
            id INTEGER PRIMARY KEY,
            driver_id INTEGER NOT NULL,
            idempotency_key TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            ride_id INTEGER,
            action TEXT,
            status_code INTEGER,
            response_json TEXT,
            state TEXT NOT NULL DEFAULT 'in_progress',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_driver_idempo_key_endpoint "
        "ON driver_idempotency_replays (driver_id, idempotency_key, endpoint)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_driver_idempo_driver "
        "ON driver_idempotency_replays (driver_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_driver_idempo_endpoint "
        "ON driver_idempotency_replays (endpoint)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_driver_idempo_created "
        "ON driver_idempotency_replays (created_at)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_driver_idempo_created")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_driver_idempo_endpoint")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_driver_idempo_driver")
    conn.exec_driver_sql("DROP INDEX IF EXISTS uq_driver_idempo_key_endpoint")
    conn.exec_driver_sql("DROP TABLE IF EXISTS driver_idempotency_replays")
