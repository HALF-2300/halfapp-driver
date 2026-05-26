"""Driver approval workflow foundation (DRIVER-002).

Revision ID: 0012_driver_approvals_foundation
Revises: 0011_settlement_entries_foundation
Create Date: 2026-05-22 23:30:00
"""
from __future__ import annotations

from alembic import op

revision = "0012_driver_approvals_foundation"
down_revision = "0011_settlement_entries_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    driver_approvals_sql = """
        CREATE TABLE IF NOT EXISTS driver_approvals (
            id INTEGER PRIMARY KEY,
            driver_id INTEGER NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            reason TEXT,
            reviewed_by INTEGER,
            reviewed_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
            CHECK (status IN ('pending', 'approved', 'rejected', 'suspended'))
        )
        """
    if conn.dialect.name == "postgresql":
        driver_approvals_sql = driver_approvals_sql.replace("DATETIME", "TIMESTAMP")
    conn.exec_driver_sql(driver_approvals_sql)
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_driver_approvals_driver_id ON driver_approvals (driver_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_driver_approvals_status ON driver_approvals (status)"
    )
    # Existing drivers at migration time are grandfathered to approved (documented in DRIVER-002 report).
    conn.exec_driver_sql(
        """
        INSERT INTO driver_approvals (driver_id, status, created_at, updated_at)
        SELECT u.id, 'approved', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM users u
        WHERE u.role = 'driver'
          AND NOT EXISTS (
              SELECT 1 FROM driver_approvals da WHERE da.driver_id = u.id
          )
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP TABLE IF EXISTS driver_approvals")
