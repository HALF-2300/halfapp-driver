"""Paginated GET /drivers/me/trips and CSV export."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

import models.user  # noqa: F401
from database import SessionLocal
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus, to_storage_ride_status
from services.rate_limit import reset_rate_limits_for_tests


def _driver_headers(db) -> tuple[dict[str, str], int]:
    stamp = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"trips_drv_{stamp}@example.com",
        "Trips Driver",
        "TestPw1",
        UserRole.DRIVER,
        f"TRP{stamp}",
        driver_approval_status="approved",
    )
    user.availability = "available"
    db.commit()
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}, user.id


def test_me_trips_pagination_filters_and_export_csv():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers, driver_id = _driver_headers(db)
        rides = [
            Ride(
                customer_name="Alice",
                status=to_storage_ride_status(RideStatus.COMPLETED),
                pickup_location="Portland Airport",
                destination="Downtown",
                distance=5.0,
                duration=12,
                driver_id=driver_id,
            ),
            Ride(
                customer_name="Bob",
                status=to_storage_ride_status(RideStatus.CANCELLED),
                pickup_location="Pearl",
                destination="Sellwood",
                distance=3.0,
                duration=8,
                driver_id=driver_id,
            ),
        ]
        db.add_all(rides)
        db.commit()
        completed_id = rides[0].id
    finally:
        db.close()

    with TestClient(app) as client:
        listed = client.get(
            "/drivers/me/trips?status=completed&limit=10&offset=0",
            headers=headers,
        )
        assert listed.status_code == 200, listed.text
        body = listed.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 1
        assert all(item["status"] == "completed" for item in body["items"])

        by_id = client.get(
            f"/drivers/me/trips?q={completed_id}",
            headers=headers,
        )
        assert by_id.status_code == 200
        assert any(item["id"] == completed_id for item in by_id.json()["items"])

        by_text = client.get(
            "/drivers/me/trips?q=Portland",
            headers=headers,
        )
        assert by_text.status_code == 200
        assert any("Portland" in (item.get("pickup_location") or "") for item in by_text.json()["items"])

        export = client.get(
            "/drivers/me/trips/export.csv?status=completed",
            headers=headers,
        )
        assert export.status_code == 200
        assert "text/csv" in export.headers.get("content-type", "")
        assert "ride_id" in export.text

        legacy = client.get("/drivers/my-rides?status=completed", headers=headers)
        assert legacy.status_code == 200
        assert isinstance(legacy.json(), list)
