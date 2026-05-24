"""API spine for RIDE_FLOW_UI_PROOF_V0_2 — rider create through driver complete."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus


def _token(db, *, role: UserRole, prefix: str) -> str:
    uid = uuid.uuid4().hex[:8]
    email = f"{prefix}_{uid}@example.com"
    license_no = f"FL{uid}" if role == UserRole.DRIVER else None
    kwargs = {}
    if role == UserRole.DRIVER:
        kwargs["driver_approval_status"] = "approved"
    user = create_user(
        db,
        email,
        f"{prefix} User",
        "FlowProof1!",
        role,
        license_no,
        **kwargs,
    )
    if role == UserRole.DRIVER:
        user.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def test_rider_create_driver_accept_complete_pricing_locked():
    db = SessionLocal()
    try:
        rider_token = _token(db, role=UserRole.CUSTOMER, prefix="rider")
        driver_token = _token(db, role=UserRole.DRIVER, prefix="driver")
    finally:
        db.close()

    with TestClient(app) as client:

        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "pickup_location": "A",
                "dropoff_location": "B",
                "pickup_latitude": 45.501,
                "pickup_longitude": -73.567,
                "dropoff_latitude": 45.515,
                "dropoff_longitude": -73.58,
                "distance_km": 2.5,
            },
        )
        assert created.status_code == 200, created.text
        ride_id = created.json()["ride"]["id"]

        client.put(
            "/drivers/presence",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={"state": "available"},
        )

        available = client.get(
            "/drivers/available-rides",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        assert available.status_code == 200
        assert any(r["id"] == ride_id for r in available.json())

        client.post(f"/drivers/accept-ride/{ride_id}", headers={"Authorization": f"Bearer {driver_token}"})
        client.post(f"/drivers/arrive-pickup/{ride_id}", headers={"Authorization": f"Bearer {driver_token}"})
        client.post(f"/drivers/start-ride/{ride_id}", headers={"Authorization": f"Bearer {driver_token}"})
        done = client.post(
            f"/drivers/complete-ride/{ride_id}",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={"tip_cents": 400, "toll_cents": 200},
        )
        assert done.status_code == 200, done.text
        body = done.json()
        ride = body["ride"]
        assert ride["status"] == "completed"
        assert ride["pricing"]["financial_locked"] is True
        assert ride["pricing"]["platform_service_fee_cents"] == 150
        assert ride["pricing"]["tip_cents"] == 400
        assert ride["pricing"]["toll_cents"] == 200
        assert ride["driver_total_payout_cents"] == ride["pricing"]["driver_total_payout_cents"]
        assert body["fare_earned"] == ride["driver_total_payout_cents"] / 100
        assert ride["route_provider"] in (
            "leaflet_osm",
            "current_or_osrm",
            "osrm_self_hosted",
            "haversine_fallback",
        )
        assert ride["traffic_provider"] in ("disabled", "none")

        again = client.get("/drivers/my-rides", headers={"Authorization": f"Bearer {driver_token}"})
        row = next(r for r in again.json() if r["id"] == ride_id)
        assert row["pricing"]["financial_locked"] is True
