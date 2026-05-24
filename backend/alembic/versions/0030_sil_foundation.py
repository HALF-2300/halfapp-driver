"""Street Intelligence Layer foundation (aggregates, route quotes, proof receipts).

Revision ID: 0030_sil_foundation
Revises: 0029_driver_telemetry_points
"""
from __future__ import annotations

from alembic import op

revision = "0030_sil_foundation"
down_revision = "0029_driver_telemetry_points"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS sil_cell_aggregate (
            id INTEGER PRIMARY KEY,
            h3 VARCHAR(32) NOT NULL,
            bucket_start_ts DATETIME NOT NULL,
            bucket_minutes INTEGER NOT NULL DEFAULT 5,
            demand_count INTEGER NOT NULL DEFAULT 0,
            supply_idle_count INTEGER NOT NULL DEFAULT 0,
            fleet_samples INTEGER NOT NULL DEFAULT 0,
            unique_drivers INTEGER NOT NULL DEFAULT 0,
            fleet_speed_p50_mps REAL,
            congestion_score REAL NOT NULL DEFAULT 0,
            busy_score REAL NOT NULL DEFAULT 0,
            confidence REAL NOT NULL DEFAULT 0,
            min_k_met INTEGER NOT NULL DEFAULT 0,
            provenance_json TEXT,
            label_version VARCHAR(32) NOT NULL DEFAULT 'sil_v0.1',
            computed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_sil_cell_h3_bucket ON sil_cell_aggregate (h3, bucket_start_ts)"
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS proof_receipts (
            id INTEGER PRIMARY KEY,
            subject VARCHAR(64) NOT NULL,
            subject_id INTEGER NOT NULL,
            proof_level VARCHAR(32) NOT NULL,
            proof_reason VARCHAR(255) NOT NULL,
            receipt_payload_json TEXT NOT NULL,
            receipt_hash VARCHAR(64) NOT NULL,
            signed_by VARCHAR(64) NOT NULL DEFAULT 'halfapp-sil-v0.1',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_proof_receipts_subject ON proof_receipts (subject, subject_id)"
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS route_quotes (
            id INTEGER PRIMARY KEY,
            driver_id INTEGER NOT NULL,
            from_h3 VARCHAR(32),
            to_h3 VARCHAR(32),
            route_method VARCHAR(64) NOT NULL,
            distance_m_est REAL,
            duration_s_est INTEGER,
            geometry_json TEXT,
            confidence REAL NOT NULL DEFAULT 0,
            honesty_flags_json TEXT,
            proof_receipt_id INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(proof_receipt_id) REFERENCES proof_receipts(id)
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_route_quotes_driver_id ON route_quotes (driver_id)"
    )


def downgrade() -> None:
    op.drop_table("route_quotes")
    op.drop_table("proof_receipts")
    op.drop_table("sil_cell_aggregate")
