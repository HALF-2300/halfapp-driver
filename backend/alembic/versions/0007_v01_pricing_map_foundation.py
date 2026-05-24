"""v0.1 pricing ledger + map route foundation fields.

Revision ID: 0007_v01_pricing_map_foundation
Revises: 0006_dossier_dispatch_ledger_foundation
Create Date: 2026-05-22 18:00:00
"""
from __future__ import annotations

from alembic import op


revision = "0007_v01_pricing_map_foundation"
down_revision = "0006_dossier_dispatch_ledger_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS ride_pricing (
            ride_id INTEGER PRIMARY KEY,
            driver_shareable_fare_cents INTEGER NOT NULL DEFAULT 0,
            platform_service_fee_cents INTEGER NOT NULL DEFAULT 150,
            tip_cents INTEGER NOT NULL DEFAULT 0,
            city_fee_cents INTEGER NOT NULL DEFAULT 0,
            airport_fee_cents INTEGER NOT NULL DEFAULT 0,
            toll_cents INTEGER NOT NULL DEFAULT 0,
            accessibility_fee_cents INTEGER NOT NULL DEFAULT 0,
            tax_cents INTEGER NOT NULL DEFAULT 0,
            driver_commission_cents INTEGER NOT NULL DEFAULT 0,
            platform_commission_cents INTEGER NOT NULL DEFAULT 0,
            driver_earnings_cents INTEGER NOT NULL DEFAULT 0,
            platform_earnings_cents INTEGER NOT NULL DEFAULT 0,
            pass_through_total_cents INTEGER NOT NULL DEFAULT 0,
            total_rider_charge_cents INTEGER NOT NULL DEFAULT 0,
            financial_locked INTEGER NOT NULL DEFAULT 0,
            locked_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE
        )
        """
    )
    for col, col_type in (
        ("route_provider", "TEXT"),
        ("traffic_provider", "TEXT"),
        ("traffic_aware", "INTEGER"),
        ("route_confidence", "TEXT"),
        ("route_calculated_at", "DATETIME"),
        ("google_maps_fallback_enabled", "INTEGER DEFAULT 0"),
        ("mapbox_traffic_enabled", "INTEGER DEFAULT 0"),
    ):
        try:
            conn.exec_driver_sql(f"ALTER TABLE rides ADD COLUMN {col} {col_type}")
        except Exception:
            pass


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP TABLE IF EXISTS ride_pricing")
