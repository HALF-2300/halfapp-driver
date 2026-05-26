"""Cross-dialect helpers for Alembic revisions (SQLite dev + PostgreSQL ship target)."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Connection


def dialect_name(conn: Connection) -> str:
    return conn.dialect.name


def is_postgresql(conn: Connection) -> bool:
    return dialect_name(conn) == "postgresql"


def is_sqlite(conn: Connection) -> bool:
    return dialect_name(conn) == "sqlite"


def table_exists(conn: Connection, table: str) -> bool:
    if is_sqlite(conn):
        row = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None
    return table in inspect(conn).get_table_names()


def column_names(conn: Connection, table: str) -> set[str]:
    if is_sqlite(conn):
        return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
    return {col["name"] for col in inspect(conn).get_columns(table)}


def add_column_if_missing(conn: Connection, table: str, column: str, ddl: str) -> None:
    if column not in column_names(conn, table):
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def create_sqlite_append_only_triggers(conn: Connection, table: str) -> None:
    """SQLite-only RAISE(ABORT) guards; PostgreSQL relies on application enforcement."""
    if not is_sqlite(conn):
        return
    conn.exec_driver_sql(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_{table}_no_update
        BEFORE UPDATE ON {table}
        BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END
        """
    )
    conn.exec_driver_sql(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_{table}_no_delete
        BEFORE DELETE ON {table}
        BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END
        """
    )


def insert_seed_ignore(conn: Connection, *, sqlite_sql: str, postgresql_sql: str) -> None:
    if is_postgresql(conn):
        conn.exec_driver_sql(postgresql_sql)
    else:
        conn.exec_driver_sql(sqlite_sql)


def try_create_postgis_extension(conn: Connection) -> bool:
    if not is_postgresql(conn):
        return False
    available = conn.exec_driver_sql(
        "SELECT 1 FROM pg_available_extensions WHERE name = 'postgis'"
    ).fetchone()
    if not available:
        return False
    conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis")
    return True
