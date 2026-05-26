"""
Pytest bootstrap and per-test isolation (HALFAPP_TEST_ISOLATION_AND_P0_GATE_STABILIZATION_01).

* ``backend/`` on sys.path before imports.
* One temp SQLite DB for the session (migrations at app import).
* Per-test: wipe ORM tables, reset env flags, rate-limit buckets, FastAPI overrides.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import text

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

_USE_POSTGRES_FOR_TESTS = os.environ.get("DATABASE_URL", "").startswith("postgresql")

if not _USE_POSTGRES_FOR_TESTS:
    _fd, _db_path = tempfile.mkstemp(suffix="_pytest_halfapp.db")
    os.close(_fd)
    os.environ["DATABASE_URL"] = f"sqlite:///{_db_path.replace(os.sep, '/')}"
os.environ["HALFAPP_ENV"] = "test"
os.environ["SECRET_KEY"] = "pytest-halfapp-test-secret-32chars-minimum"
os.environ["HALFAPP_ENABLE_RIDE_SIMULATION"] = "1"
os.environ["HALFAPP_OPEN_BOARD_DISPATCH"] = "1"

# Dossier slice tests need mounted /supply|/demand|/trip; production omits this var (gate OFF).
os.environ.setdefault("HALFAPP_DOSSIER_SPINE_ENABLED", "1")

# Default for new drivers in tests — explicit per test via driver_approval_status=.
os.environ.setdefault("HALFAPP_DRIVER_APPROVAL_DEFAULT", "pending")


def _register_orm_models() -> None:
    import models.user  # noqa: F401
    import models.ride  # noqa: F401
    import models.metrics  # noqa: F401
    import models.ledger  # noqa: F401
    import models.ride_pricing  # noqa: F401
    import models.route_snapshot  # noqa: F401
    import models.settlement_entry  # noqa: F401
    import models.pricing_policy  # noqa: F401
    import models.presence  # noqa: F401
    import models.driver_approval  # noqa: F401
    import models.driver_status  # noqa: F401
    import models.ride_dispatch_log  # noqa: F401
    import models.refresh_token  # noqa: F401
    import models.payment_execution  # noqa: F401
    import models.driver_stripe_account  # noqa: F401
    import models.payment_event  # noqa: F401
    import models.stripe_transfer  # noqa: F401
    import models.stripe_payout  # noqa: F401
    import models.stripe_payout_transfer  # noqa: F401
    import models.dossier_marketplace  # noqa: F401
    import models.driver_profile  # noqa: F401
    import models.driver_app_settings  # noqa: F401
    import models.driver_idempotency_replay  # noqa: F401
    import routes.notifications  # noqa: F401


_register_orm_models()

# SQLite append-only triggers (re-applied after per-test wipe).
_APPEND_ONLY_TRIGGER_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_marketplace_ledger_no_update BEFORE UPDATE ON marketplace_ledger "
    "BEGIN SELECT RAISE(ABORT, 'marketplace_ledger is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_marketplace_ledger_no_delete BEFORE DELETE ON marketplace_ledger "
    "BEGIN SELECT RAISE(ABORT, 'marketplace_ledger is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_marketplace_ledger_events_no_update BEFORE UPDATE ON marketplace_ledger_events "
    "BEGIN SELECT RAISE(ABORT, 'marketplace_ledger_events is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_marketplace_ledger_events_no_delete BEFORE DELETE ON marketplace_ledger_events "
    "BEGIN SELECT RAISE(ABORT, 'marketplace_ledger_events is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_trip_lifecycle_events_no_update BEFORE UPDATE ON trip_lifecycle_events "
    "BEGIN SELECT RAISE(ABORT, 'trip_lifecycle_events is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_trip_lifecycle_events_no_delete BEFORE DELETE ON trip_lifecycle_events "
    "BEGIN SELECT RAISE(ABORT, 'trip_lifecycle_events is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_ledger_entries_no_update BEFORE UPDATE ON ledger_entries "
    "BEGIN SELECT RAISE(ABORT, 'ledger_entries is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_ledger_entries_no_delete BEFORE DELETE ON ledger_entries "
    "BEGIN SELECT RAISE(ABORT, 'ledger_entries is append-only'); END",
)


def _drop_sqlite_triggers(conn) -> None:
    rows = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='trigger' AND name NOT LIKE 'sqlite_%'")
    ).fetchall()
    for (name,) in rows:
        conn.execute(text(f'DROP TRIGGER IF EXISTS "{name}"'))


def _restore_sqlite_triggers(conn) -> None:
    for ddl in _APPEND_ONLY_TRIGGER_SQL:
        conn.execute(text(ddl))


def _reseed_migration_reference_data(conn, dialect_name: str) -> None:
    """Restore rows migrations insert once (wiped with per-test DELETE)."""
    ledger_accounts_cols = (
        "id, user_id, account_type, normality, label"
        if dialect_name == "sqlite"
        else "id, user_id, account_type, normality, label, created_at"
    )
    ledger_created_at = "" if dialect_name == "sqlite" else ", NOW()"
    ledger_accounts_sql = f"""
        INSERT INTO ledger_accounts ({ledger_accounts_cols})
        VALUES
            ('acct_corporate_cash', NULL, 'asset', 'DEBIT', 'Corporate Cash / Bank'{ledger_created_at}),
            ('acct_processing_expense', NULL, 'expense', 'DEBIT', 'Payment Processing Expense'{ledger_created_at}),
            ('acct_processor_payable', NULL, 'liability', 'CREDIT', 'Payment Processor Payable'{ledger_created_at}),
            ('acct_platform_revenue', NULL, 'revenue', 'CREDIT', 'Platform Revenue'{ledger_created_at})
    """
    pricing_created_col = "" if dialect_name == "sqlite" else ", created_at"
    pricing_created_val = "" if dialect_name == "sqlite" else ", NOW()"
    pricing_policies_sql = f"""
        INSERT INTO pricing_policies (
            id, market_id, city_code, pricing_version, currency,
            base_fare_cents, per_mile_cents, per_minute_cents, minimum_ride_fare_cents,
            platform_service_fee_cents, commission_rate_bps, driver_share_bps,
            wait_fee_per_minute_cents, wait_grace_period_minutes,
            cancellation_fee_cents, city_fee_cents, accessibility_fee_cents, airport_fee_cents,
            demand_multiplier_bps, traffic_aware_pricing, is_active{pricing_created_col}
        ) VALUES (
            'us-launch-v0-1', 'US-DEFAULT', NULL, 'v0.1', 'USD',
            500, 150, 25, 800,
            150, 2000, 8000,
            0, 2,
            0, 0, 0, 0,
            10000, false, true{pricing_created_val}
        )
    """
    if dialect_name == "sqlite":
        conn.execute(
            text(
                ledger_accounts_sql.replace("INSERT INTO", "INSERT OR IGNORE INTO", 1)
            )
        )
        conn.execute(
            text(
                pricing_policies_sql.replace("INSERT INTO", "INSERT OR IGNORE INTO", 1)
            )
        )
    else:
        conn.execute(
            text(
                ledger_accounts_sql
                + " ON CONFLICT (id) DO NOTHING"
            )
        )
        conn.execute(
            text(
                pricing_policies_sql
                + " ON CONFLICT (id) DO NOTHING"
            )
        )


def _wipe_database() -> None:
    from database import Base, engine

    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys=OFF"))
            _drop_sqlite_triggers(conn)
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        _reseed_migration_reference_data(conn, engine.dialect.name)
        if engine.dialect.name == "sqlite":
            _restore_sqlite_triggers(conn)
            conn.execute(text("PRAGMA foreign_keys=ON"))
    engine.dispose()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-snapshot",
        action="store_true",
        default=False,
        help="Rewrite checked-in OpenAPI path snapshot (tests/test_openapi_surface_does_not_drift.py)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "sequential_dispatch: RIDE-003 tests requiring HALFAPP_OPEN_BOARD_DISPATCH=0",
    )
    config.addinivalue_line(
        "markers",
        "claim_race: P0-G1 PostgreSQL ten-driver accept race (requires DATABASE_URL=postgresql+...)",
    )
    config.addinivalue_line(
        "markers",
        "postgres_claim_race_proof: HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01 — requires DATABASE_URL=postgresql+...",
    )


@pytest.fixture(autouse=True)
def _isolated_test_state(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Per-test DB wipe + env/dispatch mode + rate limits + dependency overrides."""
    from main import app
    from services.rate_limit import reset_rate_limits_for_tests

    _wipe_database()

    if request.node.get_closest_marker("sequential_dispatch"):
        monkeypatch.setenv("HALFAPP_OPEN_BOARD_DISPATCH", "0")
    else:
        monkeypatch.setenv("HALFAPP_OPEN_BOARD_DISPATCH", "1")

    monkeypatch.setenv("HALFAPP_ENV", "test")
    monkeypatch.setenv("HALFAPP_ENABLE_RIDE_SIMULATION", "1")
    reset_rate_limits_for_tests()
    app.dependency_overrides.clear()

    yield

    reset_rate_limits_for_tests()
    app.dependency_overrides.clear()
