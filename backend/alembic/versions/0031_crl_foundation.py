"""City Reality Layer foundation tables.

Revision ID: 0031_crl_foundation
Revises: 0030_sil_foundation
"""
from __future__ import annotations

from alembic import op

revision = "0031_crl_foundation"
down_revision = "0030_sil_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS crl_cell_snapshot (
            id INTEGER PRIMARY KEY,
            h3 VARCHAR(32) NOT NULL,
            bucket_start_ts DATETIME NOT NULL,
            bucket_minutes INTEGER NOT NULL DEFAULT 5,
            demand_count INTEGER NOT NULL DEFAULT 0,
            pickup_count INTEGER NOT NULL DEFAULT 0,
            dropoff_count INTEGER NOT NULL DEFAULT 0,
            cancel_count INTEGER NOT NULL DEFAULT 0,
            cancel_rate REAL NOT NULL DEFAULT 0,
            avg_wait_seconds REAL,
            idle_driver_count INTEGER NOT NULL DEFAULT 0,
            supply_demand_ratio REAL,
            demand_score REAL NOT NULL DEFAULT 0,
            wait_score REAL NOT NULL DEFAULT 0,
            confidence REAL NOT NULL DEFAULT 0,
            min_k_met INTEGER NOT NULL DEFAULT 0,
            unique_drivers INTEGER NOT NULL DEFAULT 0,
            computed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_crl_snapshot_h3_bucket ON crl_cell_snapshot (h3, bucket_start_ts)"
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS zone_catalog (
            zone_id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            zone_type VARCHAR(32) NOT NULL,
            h3_list_json TEXT NOT NULL,
            center_lat REAL,
            center_lng REAL,
            radius_m REAL,
            priority_weight REAL NOT NULL DEFAULT 1
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS crl_time_pattern (
            id INTEGER PRIMARY KEY,
            h3 VARCHAR(32) NOT NULL,
            hour_of_day INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL,
            avg_demand REAL NOT NULL DEFAULT 0,
            avg_supply REAL NOT NULL DEFAULT 0,
            baseline_wait_seconds REAL
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_crl_time_h3_hour ON crl_time_pattern (h3, hour_of_day, day_of_week)"
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS city_events (
            event_id INTEGER PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            event_type VARCHAR(64) NOT NULL,
            start_ts DATETIME NOT NULL,
            end_ts DATETIME NOT NULL,
            h3_center VARCHAR(32),
            center_lat REAL,
            center_lng REAL,
            radius_m REAL DEFAULT 1500,
            confidence REAL NOT NULL DEFAULT 0.8,
            notes TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS crl_cell_explanation (
            id INTEGER PRIMARY KEY,
            h3 VARCHAR(32) NOT NULL,
            bucket_start_ts DATETIME NOT NULL,
            primary_cause VARCHAR(64) NOT NULL,
            secondary_causes_json TEXT,
            confidence REAL NOT NULL DEFAULT 0,
            signals_used_json TEXT NOT NULL,
            driver_label TEXT NOT NULL,
            label_version VARCHAR(32) NOT NULL DEFAULT 'crl_v0.1',
            computed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_crl_explain_h3_bucket ON crl_cell_explanation (h3, bucket_start_ts)"
    )


def downgrade() -> None:
    op.drop_table("crl_cell_explanation")
    op.drop_table("city_events")
    op.drop_table("crl_time_pattern")
    op.drop_table("zone_catalog")
    op.drop_table("crl_cell_snapshot")
