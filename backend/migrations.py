"""Alembic migration entrypoint for the active HalfApp backend."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine

from alembic import command
from alembic.config import Config


def _alembic_config(engine: Engine) -> Config:
    backend_dir = Path(__file__).resolve().parent
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", str(engine.url))
    return config


def run_migrations(engine: Engine) -> None:
    """Apply pending Alembic migrations to the configured database."""
    config = _alembic_config(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
