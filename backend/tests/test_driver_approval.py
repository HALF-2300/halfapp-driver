"""DRIVER-002: driver approval workflow."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
import models.driver_approval  # noqa: F401
import models.driver_status  # noqa: F401
import models.metrics  # noqa: F401
import models.presence  # noqa: F401
import models.ride  # noqa: F401
import models.user  # noqa: F401
import routes.notifications  # noqa: F401
from main import app
from models.driver_approval import DriverApproval, DriverApprovalStatus
from models.ride import Ride
from models.user import User, UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_driver(db, *, approval_status: str = "pending") -> tuple[str, int]:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"drv_{uid}@example.com",
        "Approval Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status=approval_status,
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value), user.id


def _create_admin(db) -> str:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"admin_{uid}@example.com",
        "Admin",
        "pw12345",
        UserRole.ADMIN,
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _create_rider(db) -> str:
    uid = uuid.uuid4().hex[:10]
    user = create_user(db, f"rider_{uid}@example.com", "Rider", "pw12345", UserRole.CUSTOMER)
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _requested_ride(db) -> int:
    ride = Ride(
        customer_name="Approval Rider",
        status=RideStatus.REQUESTED.value,
        pickup_location="Pickup",
        destination="Dropoff",
        distance=2.0,
        pickup_latitude=45.52,
        pickup_longitude=-122.68,
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride.id


def _go_online(client: TestClient, token: str, *, lat: float = 45.52, lng: float = -122.68) -> dict:
    return client.patch(
        "/drivers/me/status",
        headers=_headers(token),
        json={"online": True, "lat": lat, "lng": lng},
    )


def test_new_driver_approval_status_is_pending():
    db = SessionLocal()
    try:
        _, driver_id = _create_driver(db, approval_status="pending")
        row = db.query(DriverApproval).filter(DriverApproval.driver_id == driver_id).one()
        assert row.status == DriverApprovalStatus.PENDING.value
    finally:
        db.close()


def test_pending_driver_go_online_returns_403_driver_not_approved():
    db = SessionLocal()
    try:
        token, _ = _create_driver(db, approval_status="pending")
    finally:
        db.close()

    with TestClient(app) as client:
        response = _go_online(client, token)

    assert response.status_code == 403, response.text
    assert response.json()["detail"]["error"] == "driver_not_approved"


def test_admin_approves_driver_then_can_go_online():
    db = SessionLocal()
    try:
        driver_token, driver_id = _create_driver(db, approval_status="pending")
        admin_token = _create_admin(db)
    finally:
        db.close()

    with TestClient(app) as client:
        patch = client.patch(
            f"/admin/drivers/{driver_id}/approval",
            headers=_headers(admin_token),
            json={"status": "approved"},
        )
        assert patch.status_code == 200, patch.text
        online = _go_online(client, driver_token)

    assert online.status_code == 200, online.text
    assert online.json()["online"] is True


def test_admin_rejects_driver_cannot_go_online():
    db = SessionLocal()
    try:
        driver_token, driver_id = _create_driver(db, approval_status="pending")
        admin_token = _create_admin(db)
    finally:
        db.close()

    with TestClient(app) as client:
        client.patch(
            f"/admin/drivers/{driver_id}/approval",
            headers=_headers(admin_token),
            json={"status": "rejected", "reason": "invalid license"},
        )
        online = _go_online(client, driver_token)

    assert online.status_code == 403
    assert online.json()["detail"]["error"] == "driver_rejected"


def test_admin_suspends_driver_cannot_accept_new_ride():
    db = SessionLocal()
    try:
        driver_token, driver_id = _create_driver(db, approval_status="approved")
        admin_token = _create_admin(db)
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, driver_token)
        client.put("/drivers/presence", headers=_headers(driver_token), json={"state": "available"})
        client.patch(
            f"/admin/drivers/{driver_id}/approval",
            headers=_headers(admin_token),
            json={"status": "suspended"},
        )
        accept = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))

    assert accept.status_code == 403, accept.text
    assert accept.json()["detail"]["error"] == "driver_suspended"


def test_rider_cannot_access_admin_approval_endpoint():
    db = SessionLocal()
    try:
        rider_token = _create_rider(db)
        driver_token, driver_id = _create_driver(db, approval_status="pending")
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.patch(
            f"/admin/drivers/{driver_id}/approval",
            headers=_headers(rider_token),
            json={"status": "approved"},
        )

    assert response.status_code == 403


def test_driver_cannot_access_admin_approval_endpoint():
    db = SessionLocal()
    try:
        driver_token, driver_id = _create_driver(db, approval_status="pending")
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.patch(
            f"/admin/drivers/{driver_id}/approval",
            headers=_headers(driver_token),
            json={"status": "approved"},
        )

    assert response.status_code == 403


def test_approved_online_driver_sees_dispatch_pool():
    db = SessionLocal()
    try:
        driver_token, _ = _create_driver(db, approval_status="approved")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, driver_token)
        client.put("/drivers/presence", headers=_headers(driver_token), json={"state": "available"})
        response = client.get("/drivers/available-rides", headers=_headers(driver_token))

    assert response.status_code == 200, response.text
    assert any(item["id"] == ride_id for item in response.json())


@pytest.mark.parametrize("approval_status", ["pending", "rejected", "suspended"])
def test_non_approved_driver_does_not_see_dispatch_pool(approval_status: str):
    db = SessionLocal()
    try:
        driver_token, _ = _create_driver(db, approval_status=approval_status)
        _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        if approval_status == "approved":
            _go_online(client, driver_token)
        client.put("/drivers/presence", headers=_headers(driver_token), json={"state": "available"})
        response = client.get("/drivers/available-rides", headers=_headers(driver_token))

    assert response.status_code == 200
    assert response.json() == []


def test_admin_lists_pending_drivers():
    db = SessionLocal()
    try:
        admin_token = _create_admin(db)
        _create_driver(db, approval_status="pending")
        _create_driver(db, approval_status="approved")
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get("/admin/drivers?status=pending", headers=_headers(admin_token))

    assert response.status_code == 200, response.text
    assert all(row["approval"]["status"] == "pending" for row in response.json())
    assert len(response.json()) >= 1


def test_admin_lists_pending_drivers_approval_status_alias():
    db = SessionLocal()
    try:
        admin_token = _create_admin(db)
        _create_driver(db, approval_status="pending")
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get(
            "/admin/drivers?approval_status=pending",
            headers=_headers(admin_token),
        )

    assert response.status_code == 200, response.text
    assert all(row["approval"]["status"] == "pending" for row in response.json())


def test_admin_suspends_driver_cannot_go_online():
    db = SessionLocal()
    try:
        driver_token, driver_id = _create_driver(db, approval_status="approved")
        admin_token = _create_admin(db)
    finally:
        db.close()

    with TestClient(app) as client:
        client.patch(
            f"/admin/drivers/{driver_id}/approval",
            headers=_headers(admin_token),
            json={"status": "suspended", "reason": "policy review"},
        )
        online = _go_online(client, driver_token)

    assert online.status_code == 403, online.text
    assert online.json()["detail"]["error"] == "driver_suspended"


def test_internal_available_drivers_excludes_non_approved():
    db = SessionLocal()
    try:
        admin_token = _create_admin(db)
        _, pending_id = _create_driver(db, approval_status="pending")
        approved_token, approved_id = _create_driver(db, approval_status="approved")
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, approved_token)
        client.put(
            "/drivers/presence",
            headers=_headers(approved_token),
            json={"state": "available"},
        )
        response = client.get("/internal/available-drivers", headers=_headers(admin_token))

    assert response.status_code == 200, response.text
    driver_ids = response.json()["driver_ids"]
    assert approved_id in driver_ids
    assert pending_id not in driver_ids


@pytest.mark.parametrize(
    "approval_status,expected_error",
    [
        ("pending", "driver_not_approved"),
        ("rejected", "driver_rejected"),
        ("suspended", "driver_suspended"),
    ],
)
def test_non_approved_driver_cannot_accept_ride(approval_status: str, expected_error: str):
    db = SessionLocal()
    try:
        driver_token, _ = _create_driver(db, approval_status=approval_status)
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        if approval_status == "approved":
            _go_online(client, driver_token)
        client.put("/drivers/presence", headers=_headers(driver_token), json={"state": "available"})
        accept = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))

    assert accept.status_code == 403, accept.text
    assert accept.json()["detail"]["error"] == expected_error


def test_approved_driver_accept_succeeds_open_board():
    db = SessionLocal()
    try:
        driver_token, _ = _create_driver(db, approval_status="approved")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, driver_token)
        client.put("/drivers/presence", headers=_headers(driver_token), json={"state": "available"})
        accept = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))

    assert accept.status_code == 200, accept.text
    assert accept.json()["ride"]["status"] == "accepted"


@pytest.mark.sequential_dispatch
def test_ride_003_cascade_skips_pending_driver():
    from models.ride_dispatch_log import RideDispatchLog
    from services.ride_dispatch_cascade import refresh_open_dispatch_offers

    db = SessionLocal()
    try:
        _, pending_id = _create_driver(db, approval_status="pending")
        approved_token, approved_id = _create_driver(db, approval_status="approved")
        ride = Ride(
            customer_name="Cascade",
            status=RideStatus.REQUESTED.value,
            pickup_latitude=45.52,
            pickup_longitude=-122.68,
            distance=1.0,
        )
        db.add(ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, approved_token)

    db = SessionLocal()
    try:
        refresh_open_dispatch_offers(db)
        db.commit()
        ride = db.query(Ride).filter(Ride.id == ride_id).one()
        assert ride.dispatch_driver_id is not None
        assert ride.dispatch_driver_id != pending_id
        assigned = (
            db.query(DriverApproval.status)
            .filter(DriverApproval.driver_id == ride.dispatch_driver_id)
            .scalar()
        )
        assert assigned == DriverApprovalStatus.APPROVED.value
        logs = db.query(RideDispatchLog).filter(RideDispatchLog.ride_id == ride_id).all()
        offered = {row.driver_id for row in logs if row.result in ("sent", "pending")}
        assert pending_id not in offered
    finally:
        db.close()


def test_patch_approval_invalid_status_returns_structured_422():
    db = SessionLocal()
    try:
        _, driver_id = _create_driver(db, approval_status="pending")
        admin_token = _create_admin(db)
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.patch(
            f"/admin/drivers/{driver_id}/approval",
            headers=_headers(admin_token),
            json={"status": "not_a_status"},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "invalid_approval_status"


def test_suspended_driver_can_complete_active_ride():
    db = SessionLocal()
    try:
        driver_token, driver_id = _create_driver(db, approval_status="approved")
        admin_token = _create_admin(db)
        ride = Ride(
            customer_name="In flight",
            status=RideStatus.IN_PROGRESS.value,
            driver_id=driver_id,
            distance=1.0,
        )
        db.add(ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        client.patch(
            f"/admin/drivers/{driver_id}/approval",
            headers=_headers(admin_token),
            json={"status": "suspended"},
        )
        complete = client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))

    assert complete.status_code == 200, complete.text


def test_suspended_driver_cannot_decline_assigned_ride():
    db = SessionLocal()
    try:
        driver_token, driver_id = _create_driver(db, approval_status="approved")
        admin_token = _create_admin(db)
        ride = Ride(
            customer_name="Assigned",
            status=RideStatus.ACCEPTED.value,
            driver_id=driver_id,
            distance=1.0,
        )
        db.add(ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        client.patch(
            f"/admin/drivers/{driver_id}/approval",
            headers=_headers(admin_token),
            json={"status": "suspended"},
        )
        decline = client.post(f"/drivers/decline-ride/{ride_id}", headers=_headers(driver_token))

    assert decline.status_code == 403, decline.text
    assert decline.json()["detail"]["error"] == "driver_suspended"

    db = SessionLocal()
    try:
        ride = db.query(Ride).filter(Ride.id == ride_id).one()
        assert ride.driver_id == driver_id
        assert ride.status == RideStatus.ACCEPTED.value
    finally:
        db.close()
