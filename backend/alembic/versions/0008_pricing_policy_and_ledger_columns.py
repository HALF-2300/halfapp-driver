"""Pricing policy table + ride_pricing ledger component columns.

Revision ID: 0008_pricing_policy_and_ledger_columns
Revises: 0007_v01_pricing_map_foundation
Create Date: 2026-05-22 20:00:00
"""
from __future__ import annotations

from alembic import op


revision = "0008_pricing_policy_and_ledger_columns"
down_revision = "0007_v01_pricing_map_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS pricing_policies (
            id TEXT PRIMARY KEY,
            market_id TEXT NOT NULL,
            city_code TEXT,
            pricing_version TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            base_fare_cents INTEGER NOT NULL,
            per_mile_cents INTEGER NOT NULL,
            per_minute_cents INTEGER NOT NULL,
            minimum_ride_fare_cents INTEGER NOT NULL,
            platform_service_fee_cents INTEGER NOT NULL,
            commission_rate_bps INTEGER NOT NULL,
            driver_share_bps INTEGER NOT NULL,
            wait_fee_per_minute_cents INTEGER NOT NULL DEFAULT 0,
            wait_grace_period_minutes INTEGER NOT NULL DEFAULT 2,
            cancellation_fee_cents INTEGER NOT NULL DEFAULT 0,
            city_fee_cents INTEGER NOT NULL DEFAULT 0,
            accessibility_fee_cents INTEGER NOT NULL DEFAULT 0,
            airport_fee_cents INTEGER NOT NULL DEFAULT 0,
            demand_multiplier_bps INTEGER NOT NULL DEFAULT 10000,
            traffic_aware_pricing INTEGER NOT NULL DEFAULT 0,
            active_from DATETIME,
            active_to DATETIME,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.exec_driver_sql(
        """
        INSERT OR IGNORE INTO pricing_policies (
            id, market_id, city_code, pricing_version, currency,
            base_fare_cents, per_mile_cents, per_minute_cents, minimum_ride_fare_cents,
            platform_service_fee_cents, commission_rate_bps, driver_share_bps,
            wait_fee_per_minute_cents, wait_grace_period_minutes,
            cancellation_fee_cents, city_fee_cents, accessibility_fee_cents, airport_fee_cents,
            demand_multiplier_bps, traffic_aware_pricing, is_active
        ) VALUES (
            'us-launch-v0-1', 'US-DEFAULT', NULL, 'v0.1', 'USD',
            500, 150, 25, 800,
            150, 2000, 8000,
            0, 2,
            0, 0, 0, 0,
            10000, 0, 1
        )
        """
    )
    for col, col_type in (
        ("pricing_policy_id", "TEXT"),
        ("pricing_version", "TEXT"),
        ("market_id", "TEXT"),
        ("base_fare_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("distance_fare_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("time_fare_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("wait_fee_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("cancellation_fee_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("driver_ride_payout_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("platform_revenue_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("customer_total_cents", "INTEGER NOT NULL DEFAULT 0"),
        ("fare_locked_at", "DATETIME"),
    ):
        try:
            conn.exec_driver_sql(f"ALTER TABLE ride_pricing ADD COLUMN {col} {col_type}")
        except Exception:
            pass


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP TABLE IF EXISTS pricing_policies")
