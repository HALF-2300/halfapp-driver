"""Driver app settings (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02).

Revision ID: 0025_driver_settings
Revises: 0024_driver_profiles
"""
from __future__ import annotations

from alembic import op

revision = "0025_driver_settings"
down_revision = "0024_driver_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS driver_settings (
            driver_id INTEGER PRIMARY KEY,
            units TEXT NOT NULL DEFAULT 'mi',
            locale TEXT NOT NULL DEFAULT 'en-US',
            theme TEXT NOT NULL DEFAULT 'system',
            notif_push_enabled INTEGER NOT NULL DEFAULT 0,
            notif_sound_enabled INTEGER NOT NULL DEFAULT 1,
            notif_quiet_hours_json TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP TABLE IF EXISTS driver_settings")
