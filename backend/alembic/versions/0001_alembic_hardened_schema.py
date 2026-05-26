"""Initialize Alembic-owned hardened schema.

Revision ID: 0001_alembic_hardened_schema
Revises:
Create Date: 2026-05-18 10:38:00
"""
from __future__ import annotations

import re

from alembic import op

from db_migration_helpers import is_postgresql, table_exists


revision = "0001_alembic_hardened_schema"
down_revision = None
branch_labels = None
depends_on = None


TABLE_ORDER = (
    "notifications",
    "marketplace_ledger",
    "ride_claim_attempts",
    "ride_visibility",
    "metrics",
    "events",
    "rides",
    "users",
)


def _strip_check_constraints(statement: str) -> str:
    """Remove inline CHECK (...) clauses from a CREATE TABLE statement.

    This migration keeps SQLite-friendly CHECK constraints in the source SQL, but for
    PostgreSQL we strip them out. We can't use a naive regex because CHECK clauses may
    contain nested parentheses (e.g. IN (0, 1)).
    """

    marker = " CHECK "
    while True:
        idx = statement.find(marker)
        if idx == -1:
            return statement
        open_paren = statement.find("(", idx)
        if open_paren == -1:
            return statement
        depth = 0
        close_paren = None
        for j in range(open_paren, len(statement)):
            ch = statement[j]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    close_paren = j
                    break
        if close_paren is None:
            return statement
        # Drop: " CHECK (<balanced>)"
        statement = statement[:idx] + statement[close_paren + 1 :]


def _table_exists(conn, table: str) -> bool:
    row = conn.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}


def _rename_existing_tables(conn) -> dict[str, str]:
    renamed: dict[str, str] = {}
    for table in TABLE_ORDER:
        if _table_exists(conn, table):
            old_name = f"_alembic_old_{table}"
            if _table_exists(conn, old_name):
                conn.exec_driver_sql(f"DROP TABLE {old_name}")
            conn.exec_driver_sql(f"ALTER TABLE {table} RENAME TO {old_name}")
            renamed[table] = old_name
    return renamed


def _copy_table(conn, table: str, old_table: str, columns: list[str], overrides: dict[str, str] | None = None) -> None:
    old_columns = _columns(conn, old_table)
    overrides = overrides or {}
    select_exprs = []
    insert_columns = []
    for column in columns:
        expression = overrides.get(column)
        if expression is None:
            if column not in old_columns:
                continue
            expression = column
        insert_columns.append(column)
        select_exprs.append(f"{expression} AS {column}")

    if not insert_columns:
        return

    conn.exec_driver_sql(
        f"""
        INSERT INTO {table} ({", ".join(insert_columns)})
        SELECT {", ".join(select_exprs)}
        FROM {old_table}
        """
    )


def _create_schema(conn) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email VARCHAR NOT NULL UNIQUE,
            name VARCHAR NOT NULL,
            password_hash VARCHAR NOT NULL,
            role VARCHAR(8) NOT NULL,
            license_no VARCHAR UNIQUE,
            is_active BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            phone VARCHAR,
            emergency_contact VARCHAR,
            vehicle_make VARCHAR,
            vehicle_model VARCHAR,
            vehicle_year INTEGER,
            license_plate VARCHAR,
            insurance_policy VARCHAR,
            availability VARCHAR NOT NULL DEFAULT 'available',
            last_latitude FLOAT,
            last_longitude FLOAT,
            last_location_at DATETIME
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)",
        "CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)",
        "CREATE INDEX IF NOT EXISTS ix_users_availability ON users (availability)",
        """
        CREATE TABLE IF NOT EXISTS rides (
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
        """,
        "CREATE INDEX IF NOT EXISTS ix_rides_id ON rides (id)",
        "CREATE INDEX IF NOT EXISTS ix_rides_driver_id ON rides (driver_id)",
        "CREATE INDEX IF NOT EXISTS ix_rides_customer_id ON rides (customer_id)",
        "CREATE INDEX IF NOT EXISTS ix_rides_status_driver_id ON rides (status, driver_id)",
        "CREATE INDEX IF NOT EXISTS ix_rides_created_at ON rides (created_at)",
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            title VARCHAR NOT NULL,
            message TEXT NOT NULL,
            type VARCHAR DEFAULT 'info',
            is_read BOOLEAN NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
            created_at DATETIME,
            expires_at DATETIME
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_notifications_id ON notifications (id)",
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id)",
        """
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY,
            metric_name VARCHAR NOT NULL,
            value FLOAT NOT NULL,
            ride_id INTEGER REFERENCES rides(id),
            driver_id INTEGER REFERENCES users(id),
            timestamp DATETIME NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_metrics_id ON metrics (id)",
        "CREATE INDEX IF NOT EXISTS ix_metrics_metric_name ON metrics (metric_name)",
        "CREATE INDEX IF NOT EXISTS ix_metrics_ride_id ON metrics (ride_id)",
        "CREATE INDEX IF NOT EXISTS ix_metrics_driver_id ON metrics (driver_id)",
        """
        CREATE TABLE IF NOT EXISTS ride_visibility (
            id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL REFERENCES rides(id),
            driver_id INTEGER NOT NULL REFERENCES users(id),
            first_seen_at DATETIME NOT NULL,
            last_seen_at DATETIME,
            dismissed_at DATETIME,
            status VARCHAR NOT NULL DEFAULT 'visible',
            ordering_rank INTEGER NOT NULL,
            ordering_score FLOAT,
            why_this_rank_json TEXT,
            policy_version VARCHAR NOT NULL,
            metadata_json TEXT
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_ride_visibility_ride_driver ON ride_visibility (ride_id, driver_id)",
        "CREATE INDEX IF NOT EXISTS ix_ride_visibility_driver_dismissed ON ride_visibility (driver_id, dismissed_at)",
        "CREATE INDEX IF NOT EXISTS ix_ride_visibility_ride_id ON ride_visibility (ride_id)",
        """
        CREATE TABLE IF NOT EXISTS ride_claim_attempts (
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
        "CREATE INDEX IF NOT EXISTS ix_ride_claim_attempts_ride_id ON ride_claim_attempts (ride_id)",
        "CREATE INDEX IF NOT EXISTS ix_ride_claim_attempts_driver_id ON ride_claim_attempts (driver_id)",
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY,
            occurred_at DATETIME NOT NULL,
            entity_type VARCHAR NOT NULL,
            entity_id INTEGER NOT NULL,
            event_type VARCHAR NOT NULL,
            actor_id INTEGER REFERENCES users(id),
            payload_json TEXT,
            policy_version VARCHAR
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_events_entity ON events (entity_type, entity_id)",
        "CREATE INDEX IF NOT EXISTS ix_events_occurred_at ON events (occurred_at)",
        """
        CREATE TABLE IF NOT EXISTS marketplace_ledger (
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
        "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_ride_id ON marketplace_ledger (ride_id)",
        "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_driver_id ON marketplace_ledger (driver_id)",
        "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_occurred_at ON marketplace_ledger (occurred_at)",
        "CREATE TRIGGER IF NOT EXISTS trg_marketplace_ledger_no_update BEFORE UPDATE ON marketplace_ledger BEGIN SELECT RAISE(ABORT, 'marketplace_ledger is append-only'); END",
        "CREATE TRIGGER IF NOT EXISTS trg_marketplace_ledger_no_delete BEFORE DELETE ON marketplace_ledger BEGIN SELECT RAISE(ABORT, 'marketplace_ledger is append-only'); END",
    ]
    for statement in statements:
        if is_postgresql(conn):
            if "CREATE TRIGGER" in statement:
                continue
            statement = _strip_check_constraints(statement)
            statement = statement.replace(
                "BOOLEAN NOT NULL DEFAULT 1", "BOOLEAN NOT NULL DEFAULT true"
            ).replace("BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT false")
            statement = re.sub(r"\bDATETIME\b", "TIMESTAMP", statement)
            if "CREATE TABLE" in statement:
                statement = statement.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY", 1)
                # If a trailing CHECK(...) was removed, we may end up with a dangling comma.
                statement = re.sub(r",\s*\n(\s*\))", r"\n\1", statement)
        conn.exec_driver_sql(statement)


def _upgrade_postgresql_fresh(conn) -> None:
    """Greenfield PostgreSQL: create hardened schema without SQLite PRAGMA/triggers."""
    if table_exists(conn, "users"):
        return
    _create_schema(conn)


def _copy_existing_data(conn, renamed: dict[str, str]) -> None:
    if "users" in renamed:
        _copy_table(
            conn,
            "users",
            renamed["users"],
            [
                "id",
                "email",
                "name",
                "password_hash",
                "role",
                "license_no",
                "is_active",
                "created_at",
                "phone",
                "emergency_contact",
                "vehicle_make",
                "vehicle_model",
                "vehicle_year",
                "license_plate",
                "insurance_policy",
                "availability",
                "last_latitude",
                "last_longitude",
                "last_location_at",
            ],
            {
                "is_active": "CASE WHEN lower(CAST(is_active AS TEXT)) IN ('1', 'true', 't', 'yes') THEN 1 ELSE 0 END",
            },
        )
    if "rides" in renamed:
        _copy_table(
            conn,
            "rides",
            renamed["rides"],
            [
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
            ],
            {"status": "COALESCE(status, 'requested')"},
        )
    if "notifications" in renamed:
        _copy_table(
            conn,
            "notifications",
            renamed["notifications"],
            ["id", "user_id", "title", "message", "type", "is_read", "created_at", "expires_at"],
            {
                "is_read": "CASE WHEN lower(CAST(is_read AS TEXT)) IN ('1', 'true', 't', 'yes') THEN 1 ELSE 0 END",
            },
        )
    if "marketplace_ledger" in renamed:
        _copy_table(
            conn,
            "marketplace_ledger",
            renamed["marketplace_ledger"],
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
        )
    if "metrics" in renamed:
        old_columns = _columns(conn, renamed["metrics"])
        _copy_table(
            conn,
            "metrics",
            renamed["metrics"],
            ["id", "metric_name", "value", "ride_id", "driver_id", "timestamp"],
            {
                "metric_name": "metric_name" if "metric_name" in old_columns else "name",
                "timestamp": "timestamp" if "timestamp" in old_columns else "created_at",
            },
        )
    if "ride_visibility" in renamed:
        old_columns = _columns(conn, renamed["ride_visibility"])
        _copy_table(
            conn,
            "ride_visibility",
            renamed["ride_visibility"],
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
            {
                "last_seen_at": "COALESCE(last_seen_at, first_seen_at)",
                "status": "COALESCE(status, 'visible')" if "status" in old_columns else "'visible'",
                "ordering_rank": "COALESCE(ordering_rank, 0)" if "ordering_rank" in old_columns else "0",
                "policy_version": (
                    "COALESCE(policy_version, 'ranked_open_board_v1')"
                    if "policy_version" in old_columns
                    else "'ranked_open_board_v1'"
                ),
            },
        )
    if "ride_claim_attempts" in renamed:
        old_columns = _columns(conn, renamed["ride_claim_attempts"])
        _copy_table(
            conn,
            "ride_claim_attempts",
            renamed["ride_claim_attempts"],
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
            {
                "policy_version": (
                    "COALESCE(policy_version, 'ranked_open_board_v1')"
                    if "policy_version" in old_columns
                    else "'ranked_open_board_v1'"
                )
            },
        )
    if "events" in renamed:
        _copy_table(
            conn,
            "events",
            renamed["events"],
            [
                "event_id",
                "occurred_at",
                "entity_type",
                "entity_id",
                "event_type",
                "actor_id",
                "payload_json",
                "policy_version",
            ],
        )


def upgrade() -> None:
    conn = op.get_bind()
    if is_postgresql(conn):
        _upgrade_postgresql_fresh(conn)
        return
    conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
    renamed = _rename_existing_tables(conn)
    _create_schema(conn)
    _copy_existing_data(conn, renamed)
    for old_table in renamed.values():
        conn.exec_driver_sql(f"DROP TABLE {old_table}")
    conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    violations = conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"foreign key violations after migration: {violations}")


def downgrade() -> None:
    raise RuntimeError("Downgrading the hardened schema would remove integrity guarantees.")
