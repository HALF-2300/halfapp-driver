from datetime import timedelta
import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
import models.metrics  # noqa: F401
import models.presence  # noqa: F401
import models.ride  # noqa: F401
import models.user  # noqa: F401
import routes.notifications  # noqa: F401
from main import app
from models.ledger import MarketplaceLedgerEvent
from models.metrics import RideVisibility
from models.presence import DriverPresence
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.datetime_utils import utc_now_naive
from services.ledger import MarketplaceLedgerEventType


def _driver_token(db, prefix: str = "truth") -> tuple[str, int]:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"{prefix}_driver_{uid}@example.com",
        "Truth Driver",
        "pw12345",
        UserRole.DRIVER,
        f"TDL{uid}",
        driver_approval_status="approved",
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value), user.id


def _go_online(client: TestClient, headers: dict[str, str]) -> None:
    response = client.patch(
        "/drivers/me/status",
        headers=headers,
        json={"online": True, "lat": 45.501, "lng": -122.681},
    )
    assert response.status_code == 200, response.text
    presence = client.put("/drivers/presence", headers=headers, json={"state": "available"})
    assert presence.status_code == 200, presence.text


def _requested_ride(db, name: str = "Truth Rider") -> int:
    ride = Ride(
        customer_name=name,
        status="requested",
        pickup_location="Truth Pickup",
        destination="Truth Dropoff",
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


def test_presence_get_put_and_reload_are_backend_owned():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "presence")
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        initial = client.get("/drivers/presence", headers=headers)
        assert initial.status_code == 200, initial.text
        assert initial.json()["state"] == "offline"

        updated = client.put("/drivers/presence", headers=headers, json={"state": "available"})
        assert updated.status_code == 200, updated.text
        assert updated.json()["state"] == "available"
        assert updated.json()["heartbeat_at"] is not None

        reloaded = client.get("/drivers/presence", headers=headers)
        assert reloaded.status_code == 200, reloaded.text
        assert reloaded.json()["state"] == "available"

    db = SessionLocal()
    try:
        row = db.query(DriverPresence).filter(DriverPresence.driver_id == driver_id).one()
        assert row.requested_state == "available"
        assert row.heartbeat_at is not None
    finally:
        db.close()


def test_heartbeat_updates_persisted_timestamp_and_backend_derives_stale_disconnected():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "heartbeat")
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        online = client.put("/drivers/presence", headers=headers, json={"state": "available"})
        assert online.status_code == 200, online.text
        heartbeat = client.post("/drivers/heartbeat", headers=headers)
        assert heartbeat.status_code == 200, heartbeat.text
        heartbeat_at = heartbeat.json()["heartbeat_at"]

    db = SessionLocal()
    try:
        row = db.query(DriverPresence).filter(DriverPresence.driver_id == driver_id).one()
        assert row.heartbeat_at.isoformat() == heartbeat_at
        row.heartbeat_at = utc_now_naive() - timedelta(seconds=120)
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        stale = client.get("/drivers/presence", headers=headers)
        assert stale.status_code == 200, stale.text
        assert stale.json()["state"] == "stale"
        assert stale.json()["stale_reason"] == "heartbeat_older_than_90s"

    db = SessionLocal()
    try:
        row = db.query(DriverPresence).filter(DriverPresence.driver_id == driver_id).one()
        row.heartbeat_at = utc_now_naive() - timedelta(seconds=360)
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        disconnected = client.get("/drivers/presence", headers=headers)
        assert disconnected.status_code == 200, disconnected.text
        assert disconnected.json()["state"] == "disconnected"
        assert disconnected.json()["stale_reason"] == "heartbeat_older_than_300s"


def test_hide_creates_dismissal_and_excludes_only_that_driver():
    db = SessionLocal()
    try:
        first_token, first_driver_id = _driver_token(db, "hide_a")
        second_token, _ = _driver_token(db, "hide_b")
        ride_id = _requested_ride(db, "Hidden Truth Rider")
    finally:
        db.close()

    first_headers = {"Authorization": f"Bearer {first_token}"}
    second_headers = {"Authorization": f"Bearer {second_token}"}

    with TestClient(app) as client:
        _go_online(client, first_headers)
        _go_online(client, second_headers)
        first_available = client.get("/drivers/available-rides", headers=first_headers)
        assert first_available.status_code == 200, first_available.text
        assert ride_id in [ride["id"] for ride in first_available.json()]

        hidden = client.post(
            f"/drivers/rides/{ride_id}/hide",
            headers=first_headers,
            json={"reason": "not_now"},
        )
        assert hidden.status_code == 200, hidden.text

        after_hide = client.get("/drivers/available-rides", headers=first_headers)
        assert after_hide.status_code == 200, after_hide.text
        assert ride_id not in [ride["id"] for ride in after_hide.json()]

        second_available = client.get("/drivers/available-rides", headers=second_headers)
        assert second_available.status_code == 200, second_available.text
        assert ride_id in [ride["id"] for ride in second_available.json()]

    db = SessionLocal()
    try:
        visibility = (
            db.query(RideVisibility)
            .filter(RideVisibility.ride_id == ride_id, RideVisibility.driver_id == first_driver_id)
            .one()
        )
        assert visibility.status == "hidden_by_driver"
        assert visibility.reason == "not_now"
        assert visibility.dismissed_at is not None
        assert visibility.expires_at is not None
        assert visibility.correlation_id
    finally:
        db.close()


def test_simulated_reload_preserves_presence_and_hide_state():
    """New HTTP session (browser refresh) must read the same backend truth."""
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "reload")
        ride_id = _requested_ride(db, "Reload Truth Rider")
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as first_session:
        assert first_session.put("/drivers/presence", headers=headers, json={"state": "available"}).status_code == 200
        assert first_session.post("/drivers/heartbeat", headers=headers).status_code == 200
        assert ride_id in [r["id"] for r in first_session.get("/drivers/available-rides", headers=headers).json()]
        assert first_session.post(
            f"/drivers/rides/{ride_id}/hide",
            headers=headers,
            json={"reason": "reload_test"},
        ).status_code == 200
        assert ride_id not in [r["id"] for r in first_session.get("/drivers/available-rides", headers=headers).json()]

    with TestClient(app) as reloaded_session:
        presence = reloaded_session.get("/drivers/presence", headers=headers)
        assert presence.status_code == 200, presence.text
        assert presence.json()["state"] == "available"
        available = reloaded_session.get("/drivers/available-rides", headers=headers)
        assert available.status_code == 200, available.text
        assert ride_id not in [r["id"] for r in available.json()]

    db = SessionLocal()
    try:
        row = db.query(DriverPresence).filter(DriverPresence.driver_id == driver_id).one()
        assert row.requested_state == "available"
        visibility = (
            db.query(RideVisibility)
            .filter(RideVisibility.ride_id == ride_id, RideVisibility.driver_id == driver_id)
            .one()
        )
        assert visibility.status == "hidden_by_driver"
    finally:
        db.close()


def test_hidden_ride_reappears_only_after_backend_ttl_expires():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "ttl")
        ride_id = _requested_ride(db, "TTL Truth Rider")
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        client.put("/drivers/presence", headers=headers, json={"state": "available"})
        client.post(f"/drivers/rides/{ride_id}/hide", headers=headers, json={"reason": "ttl_test"})
        assert ride_id not in [r["id"] for r in client.get("/drivers/available-rides", headers=headers).json()]

    db = SessionLocal()
    try:
        visibility = (
            db.query(RideVisibility)
            .filter(RideVisibility.ride_id == ride_id, RideVisibility.driver_id == driver_id)
            .one()
        )
        visibility.expires_at = utc_now_naive() - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        available = client.get("/drivers/available-rides", headers=headers)
        assert available.status_code == 200, available.text
        assert ride_id in [r["id"] for r in available.json()]


def test_presence_hide_and_visibility_write_marketplace_ledger_events():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "ledger_truth")
        ride_id = _requested_ride(db, "Ledger Truth Rider")
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        client.put("/drivers/presence", headers=headers, json={"state": "available"})
        client.post("/drivers/heartbeat", headers=headers)
        visible = client.get("/drivers/available-rides", headers=headers)
        assert visible.status_code == 200
        client.post(f"/drivers/rides/{ride_id}/hide", headers=headers, json={"reason": "ledger"})

    db = SessionLocal()
    try:
        driver_events = {
            row.event_type
            for row in db.query(MarketplaceLedgerEvent).filter(MarketplaceLedgerEvent.driver_id == driver_id)
        }
        ride_events = {
            row.event_type
            for row in db.query(MarketplaceLedgerEvent).filter(MarketplaceLedgerEvent.ride_id == ride_id)
        }
        assert MarketplaceLedgerEventType.PRESENCE_CHANGED.value in driver_events
        assert MarketplaceLedgerEventType.PRESENCE_HEARTBEAT.value in driver_events
        assert MarketplaceLedgerEventType.DISPATCH_RIDE_VISIBLE.value in ride_events
        assert MarketplaceLedgerEventType.RIDE_HIDDEN.value in ride_events
    finally:
        db.close()


def test_available_rides_records_visibility_metadata():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "visibility")
        ride_id = _requested_ride(db, "Visible Truth Rider")
    finally:
        db.close()

    with TestClient(app) as client:
        headers = {"Authorization": f"Bearer {token}"}
        _go_online(client, headers)
        response = client.get("/drivers/available-rides", headers=headers)
        assert response.status_code == 200, response.text
        ride = next(item for item in response.json() if item["id"] == ride_id)
        assert ride["ordering_rank"] is not None
        assert ride["policy_version"] == "ranked_open_board_v1"

    db = SessionLocal()
    try:
        visibility = (
            db.query(RideVisibility)
            .filter(RideVisibility.ride_id == ride_id, RideVisibility.driver_id == driver_id)
            .one()
        )
        assert visibility.first_seen_at is not None
        assert visibility.policy_version == "ranked_open_board_v1"
        assert visibility.ordering_rank > 0
        assert visibility.correlation_id
    finally:
        db.close()
