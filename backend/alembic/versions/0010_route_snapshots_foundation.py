"""Route snapshots foundation — durable backend route evidence.

Revision ID: 0010_route_snapshots_foundation
Revises: 0009_traffic_signal_aware
Create Date: 2026-05-22 22:00:00
"""
from __future__ import annotations

from alembic import op

from db_migration_helpers import is_postgresql

revision = "0010_route_snapshots_foundation"
down_revision = "0009_traffic_signal_aware"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    route_snapshots_sql = """
        CREATE TABLE IF NOT EXISTS route_snapshots (
            id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL,
            snapshot_role TEXT NOT NULL,
            route_provider TEXT NOT NULL,
            used_fallback INTEGER NOT NULL DEFAULT 0,
            distance_meters INTEGER NOT NULL DEFAULT 0,
            duration_seconds INTEGER NOT NULL DEFAULT 0,
            geometry_polyline TEXT,
            geometry_hash TEXT,
            request_hash TEXT,
            response_hash TEXT,
            provenance_json TEXT,
            pricing_id INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE,
            FOREIGN KEY (pricing_id) REFERENCES ride_pricing(ride_id) ON DELETE SET NULL,
            CHECK (snapshot_role IN ('quote', 'accept', 'complete', 'refresh', 'diagnostic')),
            CHECK (distance_meters >= 0),
            CHECK (duration_seconds >= 0)
        )
        """
    if is_postgresql(conn):
        route_snapshots_sql = route_snapshots_sql.replace("DATETIME", "TIMESTAMP")
    conn.exec_driver_sql(route_snapshots_sql)
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_route_snapshots_ride_id ON route_snapshots (ride_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_route_snapshots_ride_role ON route_snapshots (ride_id, snapshot_role)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP TABLE IF EXISTS route_snapshots")
