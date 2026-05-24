from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from alembic.operations import ops
from sqlalchemy import engine_from_config, pool

from database import Base

# Import active ORM modules so Alembic metadata tracks the live schema.
import models.metrics  # noqa: F401
import models.ledger  # noqa: F401
import models.presence  # noqa: F401
import models.driver_status  # noqa: F401
import models.driver_approval  # noqa: F401
import models.ride  # noqa: F401
import models.user  # noqa: F401
import routes.notifications  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata

_LOCAL_LEGACY_TABLES = {"admin_invites", "drivers", "schema_migrations"}


def include_object(object_, name, type_, reflected, compare_to):  # noqa: ANN001
    if type_ == "table" and reflected and compare_to is None and name in _LOCAL_LEGACY_TABLES:
        return False
    return True


def _is_sqlite_primary_key_noise(operation) -> bool:
    """Ignore SQLite reflection noise for integer primary key nullability."""
    return (
        isinstance(operation, ops.AlterColumnOp)
        and operation.column_name in {"id", "event_id"}
        and operation.modify_type is None
        and operation.modify_server_default is False
    )


def _strip_sqlite_primary_key_noise(container) -> None:
    cleaned = []
    for operation in container.ops:
        if hasattr(operation, "ops"):
            _strip_sqlite_primary_key_noise(operation)
            if operation.ops:
                cleaned.append(operation)
            continue
        if _is_sqlite_primary_key_noise(operation):
            continue
        cleaned.append(operation)
    container.ops = cleaned


def process_revision_directives(context_, revision, directives) -> None:  # noqa: ARG001
    if not directives:
        return
    script = directives[0]
    _strip_sqlite_primary_key_noise(script.upgrade_ops)
    _strip_sqlite_primary_key_noise(script.downgrade_ops)
    if getattr(config.cmd_opts, "autogenerate", False) and script.upgrade_ops.is_empty():
        directives[:] = []


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        process_revision_directives=process_revision_directives,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    existing_connection = config.attributes.get("connection")
    if existing_connection is not None:
        context.configure(
            connection=existing_connection,
            target_metadata=target_metadata,
            include_object=include_object,
            process_revision_directives=process_revision_directives,
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            process_revision_directives=process_revision_directives,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
