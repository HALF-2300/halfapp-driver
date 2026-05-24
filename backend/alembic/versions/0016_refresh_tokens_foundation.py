"""Refresh token foundation (HALFAPP_AUTH_REFRESH_REVOCATION_01).

Revision ID: 0016_refresh_tokens_foundation
Revises: 0015_dispatch_log_reason
"""
from __future__ import annotations

from alembic import op

revision = "0016_refresh_tokens_foundation"
down_revision = "0015_dispatch_log_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL,
            last_used_at DATETIME,
            revoked_at DATETIME,
            revoke_reason TEXT,
            replaced_by_hash TEXT,
            user_agent TEXT,
            ip TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id)"
    )
    conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens (token_hash)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_active ON refresh_tokens (user_id, revoked_at)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_refresh_tokens_user_active")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_refresh_tokens_token_hash")
    conn.exec_driver_sql("DROP INDEX IF EXISTS ix_refresh_tokens_user_id")
    conn.exec_driver_sql("DROP TABLE IF EXISTS refresh_tokens")
