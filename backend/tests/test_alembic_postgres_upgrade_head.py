"""P0-G1: alembic upgrade head must succeed on PostgreSQL."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from database import engine
from migrations import _alembic_config


pytestmark = [
    pytest.mark.claim_race,
    pytest.mark.skipif(
        not os.environ.get("DATABASE_URL", "").startswith("postgresql"),
        reason="requires DATABASE_URL=postgresql+psycopg2://...",
    ),
]


def test_alembic_upgrade_head_on_postgresql():
    assert engine.dialect.name == "postgresql"
    config = _alembic_config(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    version = engine.connect().execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert version == "0036_driver_readiness_fields"

    tables = set(inspect(engine).get_table_names())
    for required in ("rides", "users", "ride_claim_attempts", "marketplace_ledger_events"):
        assert required in tables
