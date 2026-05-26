"""
HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01 — ten-driver accept race on real PostgreSQL.

Requires DATABASE_URL=postgresql+psycopg2://... before pytest starts.
Schema must come from ``alembic upgrade head`` (see test_alembic_postgres_upgrade_head).
"""

from __future__ import annotations

import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func

from database import SessionLocal, engine

import models.dossier_marketplace  # noqa: F401
import models.driver_approval  # noqa: F401
import models.driver_status  # noqa: F401
import models.ledger  # noqa: F401
import models.metrics  # noqa: F401
import models.payment  # noqa: F401
import models.presence  # noqa: F401
import models.pricing_policy  # noqa: F401
import models.ride  # noqa: F401
import models.ride_dispatch_log  # noqa: F401
import models.ride_pricing  # noqa: F401
import models.route_snapshot  # noqa: F401
import models.settlement_entry  # noqa: F401
import models.user  # noqa: F401
import routes.notifications  # noqa: F401

from main import app  # noqa: E402

from models.ledger import MarketplaceLedgerEvent
from models.metrics import RideClaimAttempt
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.ledger import MarketplaceLedgerEventType

pytestmark = [
    pytest.mark.claim_race,
    pytest.mark.postgres_claim_race_proof,
    pytest.mark.skipif(
        not os.environ.get("DATABASE_URL", "").startswith("postgresql"),
        reason="HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01 requires DATABASE_URL=postgresql+...",
    ),
]

COMPETING_DRIVER_COUNT = 10
_CLAIM_LOST_ATTEMPT_OUTCOMES = ("conflict", "unavailable")


def _redact_database_url(url: str) -> str:
    if "@" not in url:
        return url.split("?")[0]
    scheme, rest = url.split("://", 1)
    creds, hostpart = rest.rsplit("@", 1)
    user = creds.split(":")[0] if ":" in creds else creds
    return f"{scheme}://{user}:****@{hostpart.split('?')[0]}"


def _driver_token(db, prefix: str) -> tuple[str, int]:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix} Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status="approved",
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value), user.id


def _requested_ride(db) -> int:
    ride = Ride(
        customer_name="Postgres Claim Race Rider",
        status="requested",
        pickup_location="Postgres Pickup",
        destination="Postgres Dropoff",
        pickup_latitude=45.501,
        pickup_longitude=-122.681,
        dropoff_latitude=45.551,
        dropoff_longitude=-122.611,
        distance=3.0,
        duration=8,
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride.id


def _claim(token: str, ride_id: int):
    with TestClient(app) as client:
        headers = {"Authorization": f"Bearer {token}"}
        client.patch(
            "/drivers/me/status",
            headers=headers,
            json={"online": True, "lat": 45.523064, "lng": -122.676483},
        )
        return client.post(
            f"/drivers/accept-ride/{ride_id}",
            headers={"Authorization": f"Bearer {token}"},
        )


def _ledger_event_counts(db, ride_id: int) -> dict[str, int]:
    """marketplace_ledger_events: direct ride_id + event_type columns (not JSON-only)."""
    won = (
        db.query(func.count(MarketplaceLedgerEvent.id))
        .filter(
            MarketplaceLedgerEvent.ride_id == ride_id,
            MarketplaceLedgerEvent.event_type == MarketplaceLedgerEventType.DISPATCH_CLAIM_WON.value,
        )
        .scalar()
        or 0
    )
    lost = (
        db.query(func.count(MarketplaceLedgerEvent.id))
        .filter(
            MarketplaceLedgerEvent.ride_id == ride_id,
            MarketplaceLedgerEvent.event_type == MarketplaceLedgerEventType.DISPATCH_CLAIM_LOST.value,
        )
        .scalar()
        or 0
    )
    return {
        "dispatch.claim_won_events": int(won),
        "dispatch.claim_lost_events": int(lost),
    }


def test_postgres_ten_driver_claim_race_proof_01(capsys):
    assert engine.dialect.name == "postgresql", "DATABASE_URL must point at PostgreSQL"

    db = SessionLocal()
    try:
        tokens = [_driver_token(db, f"pg_race_{i}")[0] for i in range(COMPETING_DRIVER_COUNT)]
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with ThreadPoolExecutor(max_workers=COMPETING_DRIVER_COUNT) as pool:
        futures = [pool.submit(_claim, token, ride_id) for token in tokens]
        responses = [future.result() for future in as_completed(futures)]

    winners = [r for r in responses if r.status_code == 200]
    conflicts = [r for r in responses if r.status_code == 409]
    other = [r for r in responses if r.status_code not in (200, 409)]

    winner_body = winners[0].json()["ride"]
    winner_driver_id = winner_body["driver_id"]
    sample_409 = conflicts[0].json()["detail"] if conflicts else None

    db = SessionLocal()
    try:
        ride = db.query(Ride).filter(Ride.id == ride_id).one()
        attempts = db.query(RideClaimAttempt).filter(RideClaimAttempt.ride_id == ride_id).all()
        claim_won_rows = sum(1 for a in attempts if a.outcome == "won")
        claim_lost_rows = sum(1 for a in attempts if a.outcome in _CLAIM_LOST_ATTEMPT_OUTCOMES)
        ledger_counts = _ledger_event_counts(db, ride_id)

        winner_ids_from_200 = [r.json()["ride"]["driver_id"] for r in winners]
        observed = {
            "database_url_redacted": _redact_database_url(os.environ.get("DATABASE_URL", "")),
            "postgres_dialect": engine.dialect.name,
            "ride_id": ride_id,
            "successful_accepts": len(winners),
            "structured_409_conflicts": len(conflicts),
            "other_status_codes": [r.status_code for r in other],
            "assigned_driver_count": 1 if ride.driver_id is not None else 0,
            "duplicate_winners": len(winner_ids_from_200) - len(set(winner_ids_from_200)),
            "ghost_assignment": not (
                ride.status == "accepted" and ride.driver_id == winner_driver_id
            ),
            "claim_attempt_rows": len(attempts),
            "claim_won_rows": claim_won_rows,
            "claim_lost_rows": claim_lost_rows,
            **ledger_counts,
            "schema_notes": {
                "ride_claim_attempts": "ride_id, driver_id, outcome (won|conflict|unavailable)",
                "marketplace_ledger_events": "ride_id + event_type columns; dispatch.claim_* values",
            },
            "representative_409_detail": sample_409,
        }
    finally:
        db.close()

    print("\n--- HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01 observed output ---")
    print(json.dumps(observed, indent=2, sort_keys=True))
    print("--- end observed output ---\n")

    assert not other, observed
    assert observed["successful_accepts"] == 1, observed
    assert observed["structured_409_conflicts"] == 9, observed
    assert observed["assigned_driver_count"] == 1, observed
    assert observed["duplicate_winners"] == 0, observed
    assert observed["ghost_assignment"] is False, observed
    assert observed["claim_attempt_rows"] == 10, observed
    assert observed["claim_won_rows"] == 1, observed
    assert observed["claim_lost_rows"] == 9, observed
    assert observed["dispatch.claim_won_events"] == 1, observed
    assert observed["dispatch.claim_lost_events"] == 9, observed

    assert sample_409 is not None
    assert sample_409["detail"] == "Ride already claimed"
    assert sample_409["claim_result"] == "lost"
    assert sample_409["truth_status"] == "backend_conflict"
    assert sample_409["reason"] == "ride_already_claimed"
    assert sample_409["assigned_driver_id"] == winner_driver_id
    assert sample_409["ride_id"] == ride_id
