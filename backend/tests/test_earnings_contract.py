"""
Earnings response shape must match `DriverEarningsResponse` from
`schemas/earnings.py` and the contract doc.
"""

import uuid

from database import SessionLocal  # noqa: F401
import models.user  # noqa: F401
import models.ride  # noqa: F401
import routes.notifications  # noqa: F401

from fastapi.testclient import TestClient
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.datetime_utils import utc_now_naive


def _driver(db):
    uid = uuid.uuid4().hex[:10]
    u = create_user(
        db,
        f"earn_drv_{uid}@example.com",
        "Earn Drv",
        "pw12345",
        UserRole.DRIVER,
        f"DLE{uid}",
        driver_approval_status="approved",
    )
    return u, create_access_token(sub=u.email, role=u.role.value)


def test_earnings_empty_returns_zero_summary():
    db = SessionLocal()
    try:
        _, token = _driver(db)
    finally:
        db.close()

    with TestClient(app) as client:
        r = client.get("/drivers/earnings", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"driver_id", "driver_name", "earnings_summary", "recent_rides"}
    s = body["earnings_summary"]
    assert s == {
        "total_earnings": 0.0,
        "weekly_earnings": 0.0,
        "today_earnings": 0.0,
        "total_rides_completed": 0,
        "weekly_rides": 0,
        "today_rides": 0,
    }
    assert body["recent_rides"] == []


def test_earnings_with_completed_ride_uses_contract_keys():
    db = SessionLocal()
    try:
        user, token = _driver(db)
        ride = Ride(
            customer_name="Earnings Rider",
            status="completed",
            driver_id=user.id,
            fare_amount=21.5,
            distance=10.0,
            duration=15,
            completed_at=utc_now_naive(),
            rating=5,
        )
        db.add(ride)
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        r = client.get("/drivers/earnings", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["earnings_summary"]["total_rides_completed"] == 1
    assert body["earnings_summary"]["total_earnings"] == 21.5
    recent = body["recent_rides"]
    assert len(recent) == 1
    item = recent[0]
    assert set(item.keys()) == {
        "id",
        "customer_name",
        "fare_amount",
        "distance_km",
        "completed_at",
        "rating",
    }
    assert item["fare_amount"] == 21.5
    assert item["distance_km"] == 10.0
    assert isinstance(item["completed_at"], str)
    assert "distance" not in item or "distance_km" in item


def test_openapi_exposes_earnings_models():
    spec = app.openapi()
    names = spec.get("components", {}).get("schemas", {})
    assert "DriverEarningsResponse" in names
    assert "EarningsSummary" in names
    assert "EarningsRecentRide" in names
    earnings_path = spec.get("paths", {}).get("/drivers/earnings", {})
    get_op = earnings_path.get("get", {})
    ok_response = get_op.get("responses", {}).get("200", {})
    schema_ref = (
        ok_response.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref", "")
    )
    assert schema_ref.endswith("/DriverEarningsResponse")
