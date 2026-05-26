"""Marketplace ledger events foundation.

Revision ID: 0005_marketplace_ledger_events_foundation
Revises: 0004_restore_schema_indexes
Create Date: 2026-05-18 12:00:00
"""
from __future__ import annotations

from alembic import op

from db_migration_helpers import create_sqlite_append_only_triggers, is_postgresql


revision = "0005_marketplace_ledger_events_foundation"
down_revision = "0004_restore_schema_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if is_postgresql(conn):
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS marketplace_ledger_events (
                id SERIAL PRIMARY KEY,
                occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                event_type VARCHAR NOT NULL,
                entity_type VARCHAR NOT NULL,
                entity_id INTEGER,
                ride_id INTEGER REFERENCES rides(id),
                actor_id INTEGER REFERENCES users(id),
                driver_id INTEGER REFERENCES users(id),
                source VARCHAR NOT NULL DEFAULT 'halfapp.backend',
                idempotency_key VARCHAR UNIQUE,
                correlation_id VARCHAR,
                payload_json TEXT NOT NULL DEFAULT '{}',
                previous_event_hash VARCHAR,
                event_hash VARCHAR NOT NULL UNIQUE,
                policy_version VARCHAR
            )
            """
        )
    else:
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS marketplace_ledger_events (
                id INTEGER PRIMARY KEY,
                occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                event_type VARCHAR NOT NULL,
                entity_type VARCHAR NOT NULL,
                entity_id INTEGER,
                ride_id INTEGER REFERENCES rides(id),
                actor_id INTEGER REFERENCES users(id),
                driver_id INTEGER REFERENCES users(id),
                source VARCHAR NOT NULL DEFAULT 'halfapp.backend',
                idempotency_key VARCHAR UNIQUE,
                correlation_id VARCHAR,
                payload_json TEXT NOT NULL DEFAULT '{}',
                previous_event_hash VARCHAR,
                event_hash VARCHAR NOT NULL UNIQUE,
                policy_version VARCHAR
            )
            """
        )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_events_occurred_at "
        "ON marketplace_ledger_events (occurred_at)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_events_event_type "
        "ON marketplace_ledger_events (event_type)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_events_entity "
        "ON marketplace_ledger_events (entity_type, entity_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_events_ride_id "
        "ON marketplace_ledger_events (ride_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_events_actor_id "
        "ON marketplace_ledger_events (actor_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_events_driver_id "
        "ON marketplace_ledger_events (driver_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_marketplace_ledger_events_correlation_id "
        "ON marketplace_ledger_events (correlation_id)"
    )
    if not is_postgresql(conn):
        create_sqlite_append_only_triggers(conn, "marketplace_ledger_events")


def downgrade() -> None:
    raise RuntimeError("Downgrading marketplace ledger events would remove append-only audit records.")
