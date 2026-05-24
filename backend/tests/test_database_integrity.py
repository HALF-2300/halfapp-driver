import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from database import SessionLocal, engine
from main import app  # noqa: F401
from models.ledger import MarketplaceLedgerEntry
from models.ride import Ride
from models.user import UserRole
from services.auth import create_user
from services.ledger import record_ledger_entry


def test_alembic_version_table_tracks_schema_head():
    from pathlib import Path

    versions_dir = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    known_revisions = {
        path.stem.split("_", 1)[0]
        for path in versions_dir.glob("*.py")
        if not path.name.startswith("__")
    }
    # revision id is the filename prefix before the first underscore in the module docstring / revision var
    known_ids = set()
    for path in versions_dir.glob("*.py"):
        if path.name.startswith("__"):
            continue
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith('revision = "'):
                known_ids.add(line.split('"')[1])
                break

    with engine.connect() as conn:
        version = conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()

    assert version in known_ids


def test_boolean_and_foreign_key_constraints_are_enforced():
    """Use independent connections; avoid nested ``begin()`` after per-test wipe."""
    uid = uuid.uuid4().hex
    with pytest.raises(IntegrityError):
        with engine.connect() as conn:
            conn.exec_driver_sql(
                """
                INSERT INTO users (email, name, password_hash, role, is_active)
                VALUES (?, 'Invalid Bool', 'hash', 'DRIVER', 2)
                """,
                (f"bad_bool_{uid}@example.com",),
            )
            conn.commit()

    with pytest.raises(IntegrityError):
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.exec_driver_sql(
                """
                INSERT INTO rides (customer_name, driver_id, status)
                VALUES ('Bad FK Rider', 99999999, 'requested')
                """
            )
            conn.commit()


def test_marketplace_ledger_is_append_only_on_disk():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:10]
        driver = create_user(
            db,
            f"ledger_driver_{uid}@example.com",
            "Ledger Driver",
            "pw12345",
            UserRole.DRIVER,
            f"LEDGER{uid}",
            driver_approval_status="approved",
        )
        ride = Ride(customer_name="Ledger Rider", status="requested", distance=1.0)
        db.add(ride)
        db.flush()
        entry = record_ledger_entry(
            db,
            event_type="claim_attempted",
            ride_id=ride.id,
            actor_id=driver.id,
            driver_id=driver.id,
            outcome="won",
        )
        db.commit()
        entry_id = entry.id
    finally:
        db.close()

    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE marketplace_ledger SET outcome = 'mutated' WHERE id = ?",
                (entry_id,),
            )

    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.exec_driver_sql("DELETE FROM marketplace_ledger WHERE id = ?", (entry_id,))

    db = SessionLocal()
    try:
        entry = db.query(MarketplaceLedgerEntry).filter(MarketplaceLedgerEntry.id == entry_id).one()
        assert entry.outcome == "won"
    finally:
        db.close()
