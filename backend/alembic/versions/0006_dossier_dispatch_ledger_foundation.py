"""Dossier dispatch + double-entry ledger foundation (REQ-06..REQ-20 slice).

Revision ID: 0006_dossier_dispatch_ledger_foundation
Revises: 0005_marketplace_ledger_events_foundation
Create Date: 2026-05-22 12:00:00
"""
from __future__ import annotations

from alembic import op

from db_migration_helpers import (
    create_sqlite_append_only_triggers,
    insert_seed_ignore,
    try_create_postgis_extension,
)


revision = "0006_dossier_dispatch_ledger_foundation"
down_revision = "0005_marketplace_ledger_events_foundation"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _pg_compat_ddl(sql: str) -> str:
    # Minimal SQLite->Postgres DDL normalization for early foundation tables.
    sql = sql.replace("DATETIME", "TIMESTAMP")
    sql = sql.replace("REAL", "DOUBLE PRECISION")
    sql = sql.replace("id INTEGER PRIMARY KEY", "id SERIAL PRIMARY KEY")
    return sql


def upgrade() -> None:
    conn = op.get_bind()
    is_postgres = _dialect_name() == "postgresql"

    has_postgis = try_create_postgis_extension(conn) if is_postgres else False

    active_drivers_sql = """
        CREATE TABLE IF NOT EXISTS active_drivers (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'OFFLINE',
            vehicle_type TEXT NOT NULL DEFAULT 'standard',
            latitude REAL,
            longitude REAL,
            heading REAL,
            velocity_mps REAL,
            device_timestamp DATETIME,
            location_updated_at DATETIME,
            available_seats INTEGER NOT NULL DEFAULT 4,
            has_child_seat INTEGER NOT NULL DEFAULT 0,
            wheelchair_access INTEGER NOT NULL DEFAULT 0,
            assigned_trip_id TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    conn.exec_driver_sql(_pg_compat_ddl(active_drivers_sql) if is_postgres else active_drivers_sql)

    if is_postgres and has_postgis:
        conn.exec_driver_sql(
            """
            ALTER TABLE active_drivers
            ADD COLUMN IF NOT EXISTS location geometry(Point, 4326)
            """
        )
        conn.exec_driver_sql(
            """
            CREATE INDEX IF NOT EXISTS ix_active_drivers_location_gist
            ON active_drivers USING GIST (location)
            """
        )
    else:
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_active_drivers_lat_lng ON active_drivers (latitude, longitude)"
        )

    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_active_drivers_status_vehicle "
        "ON active_drivers (status, vehicle_type)"
    )

    trip_lifecycle_sql = """
        CREATE TABLE IF NOT EXISTS trip_lifecycle_events (
            id INTEGER PRIMARY KEY,
            trip_id TEXT NOT NULL,
            rider_id TEXT,
            driver_id TEXT,
            from_state TEXT,
            to_state TEXT NOT NULL,
            trigger_event TEXT NOT NULL,
            idempotency_key TEXT UNIQUE,
            payload_json TEXT NOT NULL DEFAULT '{}',
            occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    conn.exec_driver_sql(_pg_compat_ddl(trip_lifecycle_sql) if is_postgres else trip_lifecycle_sql)
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_trip_lifecycle_events_trip_id "
        "ON trip_lifecycle_events (trip_id, occurred_at)"
    )

    ledger_accounts_sql = """
        CREATE TABLE IF NOT EXISTS ledger_accounts (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            account_type TEXT NOT NULL,
            normality TEXT NOT NULL CHECK (normality IN ('DEBIT', 'CREDIT')),
            label TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    conn.exec_driver_sql(_pg_compat_ddl(ledger_accounts_sql) if is_postgres else ledger_accounts_sql)
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_ledger_accounts_user_id ON ledger_accounts (user_id)"
    )

    ledger_tx_sql = """
        CREATE TABLE IF NOT EXISTS ledger_transactions (
            id TEXT PRIMARY KEY,
            reference_key TEXT UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            trip_id TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    conn.exec_driver_sql(_pg_compat_ddl(ledger_tx_sql) if is_postgres else ledger_tx_sql)

    ledger_entries_sql = """
        CREATE TABLE IF NOT EXISTS ledger_entries (
            id INTEGER PRIMARY KEY,
            transaction_id TEXT NOT NULL REFERENCES ledger_transactions(id),
            account_id TEXT NOT NULL REFERENCES ledger_accounts(id),
            amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
            direction TEXT NOT NULL CHECK (direction IN ('DEBIT', 'CREDIT')),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    conn.exec_driver_sql(_pg_compat_ddl(ledger_entries_sql) if is_postgres else ledger_entries_sql)
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_ledger_entries_transaction_id "
        "ON ledger_entries (transaction_id)"
    )

    if not is_postgres:
        create_sqlite_append_only_triggers(conn, "trip_lifecycle_events")
        create_sqlite_append_only_triggers(conn, "ledger_entries")

    if is_postgres:
        conn.exec_driver_sql(
            """
            CREATE OR REPLACE FUNCTION enforce_ledger_transaction_balance()
            RETURNS TRIGGER AS $$
            DECLARE
                debit_total BIGINT;
                credit_total BIGINT;
            BEGIN
                SELECT
                    COALESCE(SUM(amount_cents) FILTER (WHERE direction = 'DEBIT'), 0),
                    COALESCE(SUM(amount_cents) FILTER (WHERE direction = 'CREDIT'), 0)
                INTO debit_total, credit_total
                FROM ledger_entries
                WHERE transaction_id = NEW.transaction_id;

                IF debit_total <> credit_total THEN
                    RAISE EXCEPTION 'ledger transaction %% is unbalanced (debits=%%, credits=%%)',
                        NEW.transaction_id, debit_total, credit_total;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        conn.exec_driver_sql(
            """
            DROP TRIGGER IF EXISTS trg_ledger_entries_balance ON ledger_entries
            """
        )
        conn.exec_driver_sql(
            """
            CREATE CONSTRAINT TRIGGER trg_ledger_entries_balance
            AFTER INSERT ON ledger_entries
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW
            EXECUTE FUNCTION enforce_ledger_transaction_balance()
            """
        )
    # SQLite cannot defer constraint triggers; balance is enforced in application code.

    insert_seed_ignore(
        conn,
        sqlite_sql="""
        INSERT OR IGNORE INTO ledger_accounts (id, user_id, account_type, normality, label)
        VALUES
            ('acct_corporate_cash', NULL, 'asset', 'DEBIT', 'Corporate Cash / Bank'),
            ('acct_processing_expense', NULL, 'expense', 'DEBIT', 'Payment Processing Expense'),
            ('acct_processor_payable', NULL, 'liability', 'CREDIT', 'Payment Processor Payable'),
            ('acct_platform_revenue', NULL, 'revenue', 'CREDIT', 'Platform Revenue')
        """,
        postgresql_sql="""
        INSERT INTO ledger_accounts (id, user_id, account_type, normality, label)
        VALUES
            ('acct_corporate_cash', NULL, 'asset', 'DEBIT', 'Corporate Cash / Bank'),
            ('acct_processing_expense', NULL, 'expense', 'DEBIT', 'Payment Processing Expense'),
            ('acct_processor_payable', NULL, 'liability', 'CREDIT', 'Payment Processor Payable'),
            ('acct_platform_revenue', NULL, 'revenue', 'CREDIT', 'Platform Revenue')
        ON CONFLICT (id) DO NOTHING
        """,
    )


def downgrade() -> None:
    conn = op.get_bind()
    is_postgres = _dialect_name() == "postgresql"

    if is_postgres:
        conn.exec_driver_sql(
            "DROP TRIGGER IF EXISTS trg_ledger_entries_balance ON ledger_entries"
        )
        conn.exec_driver_sql("DROP FUNCTION IF EXISTS enforce_ledger_transaction_balance()")

    for table in (
        "ledger_entries",
        "ledger_transactions",
        "ledger_accounts",
        "trip_lifecycle_events",
        "active_drivers",
    ):
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
