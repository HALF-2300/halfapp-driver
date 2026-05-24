"""Canonical ride status contract.

Revision ID: 0002_canonical_ride_status_contract
Revises: 0001_alembic_hardened_schema
Create Date: 2026-05-18 11:12:00
"""
from __future__ import annotations

from alembic import op


revision = "0002_canonical_ride_status_contract"
down_revision = "0001_alembic_hardened_schema"
branch_labels = None
depends_on = None


RIDE_COLUMNS = [
    "id",
    "customer_name",
    "customer_id",
    "driver_id",
    "status",
    "pickup_location",
    "destination",
    "pickup_latitude",
    "pickup_longitude",
    "dropoff_latitude",
    "dropoff_longitude",
    "fare_amount",
    "distance",
    "duration",
    "created_at",
    "accepted_at",
    "arrived_pickup_at",
    "started_at",
    "completed_at",
    "cancelled_at",
    "lifecycle_reason",
    "notes",
    "rating",
]


def _rebuild_table(conn, table: str, create_sql: str, columns: list[str], indexes: list[str]) -> None:
    old_table = f"_alembic_old_{table}"
    conn.exec_driver_sql(f"DROP TABLE IF EXISTS {old_table}")
    conn.exec_driver_sql(f"ALTER TABLE {table} RENAME TO {old_table}")
    conn.exec_driver_sql(create_sql)
    conn.exec_driver_sql(
        f"""
        INSERT INTO {table} ({", ".join(columns)})
        SELECT {", ".join(columns)}
        FROM {old_table}
        """
    )
    conn.exec_driver_sql(f"DROP TABLE {old_table}")
    for statement in indexes:
        conn.exec_driver_sql(statement)


def _rebuild_ride_dependents(conn) -> None:
    _rebuild_table(
        conn,
        "metrics",
        """
        CREATE TABLE metrics (
            id INTEGER PRIMARY KEY,
            metric_name VARCHAR NOT NULL,
            value FLOAT NOT NULL,
            ride_id INTEGER REFERENCES rides(id),
            driver_id INTEGER REFERENCES users(id),
            timestamp DATETIME NOT NULL
        )
        """,
        ["id", "metric_name", "value", "ride_id", "driver_id", "timestamp"],
        [
            "CREATE INDEX IF NOT EXISTS ix_metrics_id ON metrics (id)",
            "CREATE INDEX IF NOT EXISTS ix_metrics_metric_name ON metrics (metric_name)",
            "CREATE INDEX IF NOT EXISTS ix_metrics_ride_id ON metrics (ride_id)",
            "CREATE INDEX IF NOT EXISTS ix_metrics_driver_id ON metrics (driver_id)",
        ],
    )
    _rebuild_table(
        conn,
        "ride_visibility",
        """
        CREATE TABLE ride_visibility (
            id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL REFERENCES rides(id),
            driver_id INTEGER NOT NULL REFERENCES users(id),
            first_seen_at DATETIME NOT NULL,
            last_seen_at DATETIME NOT NULL,
            dismissed_at DATETIME,
            status VARCHAR NOT NULL DEFAULT 'visible',
            ordering_rank INTEGER NOT NULL,
            ordering_score FLOAT,
            why_this_rank_json TEXT,
            policy_version VARCHAR NOT NULL,
            metadata_json TEXT
        )
        """,
        [
            "id",
            "ride_id",
            "driver_id",
            "first_seen_at",
            "last_seen_at",
            "dismissed_at",
            "status",
            "ordering_rank",
            "ordering_score",
            "why_this_rank_json",
            "policy_version",
            "metadata_json",
        ],
        [
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_ride_visibility_ride_driver ON ride_visibility (ride_id, driver_id)",
            "CREATE INDEX IF NOT EXISTS ix_ride_visibility_driver_dismissed ON ride_visibility (driver_id, dismissed_at)",
            "CREATE INDEX IF NOT EXISTS ix_ride_visibility_ride_id ON ride_visibility (ride_id)",
        ],
    )
    _rebuild_table(
        conn,
        "ride_claim_attempts",
        """
        CREATE TABLE ride_claim_attempts (
            id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL REFERENCES rides(id),
            driver_id INTEGER NOT NULL REFERENCES users(id),
            attempted_at DATETIME NOT NULL,
            outcome VARCHAR NOT NULL,
            competing_driver_id INTEGER REFERENCES users(id),
            reason TEXT,
            policy_version VARCHAR NOT NULL
        )
        """,
        [
            "id",
            "ride_id",
            "driver_id",
            "attempted_at",
            "outcome",
            "competing_driver_id",
            "reason",
            "policy_version",
        ],
        [
            "CREATE INDEX IF NOT EXISTS ix_ride_claim_attempts_ride_id ON ride_claim_attempts (ride_id)",
            "CREATE INDEX IF NOT EXISTS ix_ride_claim_attempts_driver_id ON ride_claim_attempts (driver_id)",
        ],
    )
    _rebuild_table(
        conn,
        "marketplace_ledger",
        """
        CREATE TABLE marketplace_ledger (
            id INTEGER PRIMARY KEY,
            occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            event_type VARCHAR NOT NULL CHECK (
                event_type IN ('claim_attempted', 'claim_won', 'claim_lost', 'claim_released')
            ),
            ride_id INTEGER REFERENCES rides(id),
            actor_id INTEGER REFERENCES users(id),
            driver_id INTEGER REFERENCES users(id),
            outcome VARCHAR,
            reason TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            prior_hash VARCHAR,
            entry_hash VARCHAR NOT NULL UNIQUE,
            policy_version VARCHAR,
            CHECK (ride_id IS NOT NULL OR event_type = 'claim_attempted')
        )
        """,
        [
            "id",
            "occurred_at",
            "event_type",
            "ride_id",
            "actor_id",
            "driver_id",
            "outcome",
            "reason",
            "payload_json",
            "prior_hash",
            "entry_hash",
            "policy_version",
        ],
        [
            "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_ride_id ON marketplace_ledger (ride_id)",
            "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_driver_id ON marketplace_ledger (driver_id)",
            "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_occurred_at ON marketplace_ledger (occurred_at)",
            "CREATE TRIGGER IF NOT EXISTS trg_marketplace_ledger_no_update BEFORE UPDATE ON marketplace_ledger BEGIN SELECT RAISE(ABORT, 'marketplace_ledger is append-only'); END",
            "CREATE TRIGGER IF NOT EXISTS trg_marketplace_ledger_no_delete BEFORE DELETE ON marketplace_ledger BEGIN SELECT RAISE(ABORT, 'marketplace_ledger is append-only'); END",
        ],
    )


def upgrade() -> None:
    conn = op.get_bind()
    ride_schema = conn.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='rides'"
    ).scalar() or ""
    if "driver_arrived" in ride_schema:
        return

    conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
    conn.exec_driver_sql("PRAGMA legacy_alter_table=ON")
    conn.exec_driver_sql("ALTER TABLE rides RENAME TO _alembic_old_rides")
    conn.exec_driver_sql(
        """
        CREATE TABLE rides (
            id INTEGER PRIMARY KEY,
            customer_name VARCHAR NOT NULL,
            customer_id INTEGER REFERENCES users(id),
            driver_id INTEGER REFERENCES users(id),
            status VARCHAR NOT NULL DEFAULT 'requested',
            pickup_location VARCHAR,
            destination VARCHAR,
            pickup_latitude FLOAT,
            pickup_longitude FLOAT,
            dropoff_latitude FLOAT,
            dropoff_longitude FLOAT,
            fare_amount FLOAT DEFAULT 0.0,
            distance FLOAT DEFAULT 0.0,
            duration INTEGER DEFAULT 0,
            created_at DATETIME,
            accepted_at DATETIME,
            arrived_pickup_at DATETIME,
            started_at DATETIME,
            completed_at DATETIME,
            cancelled_at DATETIME,
            lifecycle_reason TEXT,
            notes TEXT,
            rating INTEGER,
            CHECK (status IN (
                'requested',
                'offered',
                'accepted',
                'driver_arrived',
                'in_progress',
                'completed',
                'cancelled'
            ))
        )
        """
    )
    conn.exec_driver_sql(
        f"""
        INSERT INTO rides ({", ".join(RIDE_COLUMNS)})
        SELECT
            id,
            customer_name,
            customer_id,
            driver_id,
            CASE status
                WHEN 'arrived_at_pickup' THEN 'driver_arrived'
                WHEN 'waiting_for_rider' THEN 'driver_arrived'
                WHEN 'en_route_to_pickup' THEN 'accepted'
                ELSE COALESCE(status, 'requested')
            END AS status,
            pickup_location,
            destination,
            pickup_latitude,
            pickup_longitude,
            dropoff_latitude,
            dropoff_longitude,
            fare_amount,
            distance,
            duration,
            created_at,
            accepted_at,
            arrived_pickup_at,
            started_at,
            completed_at,
            cancelled_at,
            lifecycle_reason,
            notes,
            rating
        FROM _alembic_old_rides
        """
    )
    conn.exec_driver_sql("DROP TABLE _alembic_old_rides")
    conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_rides_id ON rides (id)")
    conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_rides_driver_id ON rides (driver_id)")
    conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_rides_customer_id ON rides (customer_id)")
    conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_rides_status_driver_id ON rides (status, driver_id)")
    conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_rides_created_at ON rides (created_at)")
    _rebuild_ride_dependents(conn)
    conn.exec_driver_sql("PRAGMA legacy_alter_table=OFF")
    conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    violations = conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"foreign key violations after migration: {violations}")


def downgrade() -> None:
    raise RuntimeError("Downgrading the canonical lifecycle contract is not supported.")
