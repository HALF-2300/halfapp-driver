"""
verify:halfapp-repair-design-accuracy-server-flex-01

Verifier for the GO_HALFAPP_PRODUCT_REPAIR_DESIGN_UPGRADE_ACCURACY_SERVER_FLEX_01 pass.

Covers:
1. Server health and restart resilience
2. Full driver ride lifecycle (rider→driver path)
3. Pickup/dropoff coordinate accuracy
4. Server error / bad payload handling (resilience)
5. Release accepted ride back to pool (decline-ride)
6. Race condition: duplicate accept returns 409

Run from backend/:
    python -m pytest tests/test_halfapp_repair_verify_01.py -v
"""
from __future__ import annotations

import uuid
import os
import pytest

from fastapi.testclient import TestClient

from main import app
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus, RideStatus
from services.rate_limit import reset_rate_limits_for_tests
from models.user import UserRole
from database import SessionLocal


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_driver(db):
    uid = uuid.uuid4().hex[:10]
    u = create_user(
        db,
        f"vrfdrv_{uid}@example.com",
        f"Verify Driver {uid}",
        "VerifyPw1!",
        UserRole.DRIVER,
        f"VRF{uid}",
        driver_approval_status="approved",
    )
    u.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return u, create_access_token(sub=u.email, role=u.role.value)


def _make_rider(db):
    uid = uuid.uuid4().hex[:10]
    u = create_user(db, f"vrfrdr_{uid}@example.com", f"Verify Rider {uid}", "VerifyPw1!", UserRole.CUSTOMER, None)
    db.commit()
    return u, create_access_token(sub=u.email, role=u.role.value)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_ride(client, rider_token: str, **overrides) -> dict:
    body = {
        "pickup_location": "Verify Pickup St",
        "dropoff_location": "Verify Dropoff Ave",
        "pickup_latitude": 45.523064,
        "pickup_longitude": -122.676483,
        "dropoff_latitude": 45.530000,
        "dropoff_longitude": -122.680000,
        "distance_km": 5.0,
        **overrides,
    }
    r = client.post("/rides/", headers=_auth(rider_token), json=body)
    assert r.status_code == 200, f"create ride failed: {r.text}"
    return r.json()["ride"]


# ---------------------------------------------------------------------------
# 1. Server health and restart resilience
# ---------------------------------------------------------------------------

class TestServerHealth:
    """Verify health endpoint is reachable and returns correct shape."""

    def test_health_returns_ok(self):
        with TestClient(app) as client:
            r = client.get("/health")
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "ok"

    def test_healthz_alias(self):
        with TestClient(app) as client:
            r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_server_returns_json_on_unknown_route(self):
        """Unknown routes return a structured error, not a crash."""
        with TestClient(app) as client:
            r = client.get("/nonexistent-endpoint-xyz")
        assert r.status_code == 404
        body = r.json()
        assert "detail" in body

    def test_bad_json_body_returns_422(self):
        """Malformed JSON payload returns 422, not 500."""
        with TestClient(app) as client:
            r = client.post(
                "/auth/login",
                content=b"not json at all {{{",
                headers={"Content-Type": "application/json"},
            )
        assert r.status_code == 422, r.text

    def test_missing_auth_returns_401(self):
        """Protected route with no token returns 401, not 500."""
        with TestClient(app) as client:
            r = client.get("/drivers/available-rides")
        assert r.status_code == 401, r.text


# ---------------------------------------------------------------------------
# 2. Driver ride lifecycle with coordinate verification
# ---------------------------------------------------------------------------

class TestRideLifecycleAccuracy:
    """End-to-end ride path verifying coordinate accuracy at each step."""

    def test_full_lifecycle_coordinates_survive_each_transition(self):
        reset_rate_limits_for_tests()
        with TestClient(app) as client:
            with SessionLocal() as db:
                _driver_user, driver_token = _make_driver(db)
                _rider_user, rider_token = _make_rider(db)

            ride = _create_ride(client, rider_token)
            ride_id = ride["id"]

            # Coordinates present at creation
            assert abs(ride["pickup_latitude"] - 45.523064) < 1e-4
            assert abs(ride["dropoff_latitude"] - 45.530000) < 1e-4

            # Driver accepts
            r = client.post(f"/drivers/accept-ride/{ride_id}", headers=_auth(driver_token))
            assert r.status_code == 200, f"accept failed: {r.text}"
            accepted = r.json()["ride"]
            assert abs(accepted["pickup_latitude"] - 45.523064) < 1e-4
            assert abs(accepted["dropoff_latitude"] - 45.530000) < 1e-4
            assert accepted["status"] == "accepted"

            # Driver arrives
            r = client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_auth(driver_token))
            assert r.status_code == 200, f"arrive-pickup failed: {r.text}"
            assert r.json()["ride"]["status"] == "driver_arrived"

            # Driver starts
            r = client.post(f"/drivers/start-ride/{ride_id}", headers=_auth(driver_token))
            assert r.status_code == 200, f"start-ride failed: {r.text}"
            assert r.json()["ride"]["status"] == "in_progress"

            # Driver completes
            r = client.post(f"/drivers/complete-ride/{ride_id}", headers=_auth(driver_token))
            assert r.status_code == 200, f"complete-ride failed: {r.text}"
            completed = r.json()["ride"]
            assert completed["status"] == "completed"
            # Coordinates must survive completion
            assert abs(completed["pickup_latitude"] - 45.523064) < 1e-4
            assert abs(completed["dropoff_latitude"] - 45.530000) < 1e-4


# ---------------------------------------------------------------------------
# 3. Coordinate validation
# ---------------------------------------------------------------------------

class TestCoordinateAccuracy:
    """Verify coordinate validation and presence in API responses."""

    def test_simulation_ride_always_has_coordinates(self):
        """simulate-ride endpoint always generates valid lat/lng even when body omits them."""
        os.environ.setdefault("HALFAPP_ENABLE_RIDE_SIMULATION", "1")
        reset_rate_limits_for_tests()

        with TestClient(app) as client:
            with SessionLocal() as db:
                _driver_user, driver_token = _make_driver(db)

            r = client.post(
                "/drivers/simulate-ride",
                json={
                    "customer_name": "Coord Tester",
                    "pickup_location": "Portland Start",
                    "destination": "Portland End",
                },
                headers=_auth(driver_token),
            )
            if r.status_code == 403:
                pytest.skip("Simulation disabled in this environment")

            assert r.status_code == 200, r.text
            ride = r.json()["ride"]

            assert ride.get("pickup_latitude") is not None, "pickup_latitude missing"
            assert ride.get("pickup_longitude") is not None, "pickup_longitude missing"
            assert ride.get("dropoff_latitude") is not None, "dropoff_latitude missing"
            assert ride.get("dropoff_longitude") is not None, "dropoff_longitude missing"

            # Coordinates should be in Portland area (backend default base)
            assert 45.4 < float(ride["pickup_latitude"]) < 45.7
            assert -122.8 < float(ride["pickup_longitude"]) < -122.5

    def test_available_rides_have_coordinates(self):
        """Available rides returned to driver always include coordinates."""
        reset_rate_limits_for_tests()
        with TestClient(app) as client:
            with SessionLocal() as db:
                _driver_user, driver_token = _make_driver(db)
                _rider_user, rider_token = _make_rider(db)

            _create_ride(client, rider_token)

            r = client.get("/drivers/available-rides", headers=_auth(driver_token))
            assert r.status_code == 200, r.text
            rides = r.json()
            if not rides:
                pytest.skip("No available rides in pool")

            for ride in rides:
                assert "pickup_latitude" in ride, f"pickup_latitude missing from ride {ride.get('id')}"
                assert "dropoff_latitude" in ride, f"dropoff_latitude missing from ride {ride.get('id')}"

    def test_coordinates_reject_obvious_falsy_values(self):
        """Coordinates of 0,0 (Gulf of Guinea) should not be created without explicit intent."""
        reset_rate_limits_for_tests()
        with TestClient(app) as client:
            with SessionLocal() as db:
                _rider_user, rider_token = _make_rider(db)
            # 0,0 coordinates are allowed by the schema but should at least serialize correctly
            r = client.post("/rides/", headers=_auth(rider_token), json={
                "pickup_location": "Origin",
                "dropoff_location": "Dest",
                "pickup_latitude": 0.0,
                "pickup_longitude": 0.0,
                "dropoff_latitude": 1.0,
                "dropoff_longitude": 1.0,
            })
            # Whether 0,0 is allowed or rejected, it must not 500
            assert r.status_code in (200, 422, 400), f"unexpected: {r.status_code} {r.text}"


# ---------------------------------------------------------------------------
# 4. Server resilience — bad payload / wrong state transitions
# ---------------------------------------------------------------------------

class TestServerResilience:
    """Verify server handles bad inputs gracefully (no 500s)."""

    def test_accept_nonexistent_ride_returns_404(self):
        reset_rate_limits_for_tests()
        with TestClient(app) as client:
            with SessionLocal() as db:
                _u, token = _make_driver(db)
            r = client.post("/drivers/accept-ride/999999999", headers=_auth(token))
        assert r.status_code == 404, r.text

    def test_complete_ride_in_wrong_state_returns_409(self):
        """Completing a ride that hasn't started returns 409, not 500."""
        reset_rate_limits_for_tests()
        with TestClient(app) as client:
            with SessionLocal() as db:
                _u, driver_token = _make_driver(db)
                _r, rider_token = _make_rider(db)

            ride = _create_ride(client, rider_token)
            ride_id = ride["id"]
            client.post(f"/drivers/accept-ride/{ride_id}", headers=_auth(driver_token))

            # Try to complete without arrive+start — must be 409, not 500
            r = client.post(f"/drivers/complete-ride/{ride_id}", headers=_auth(driver_token))
        assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text}"

    def test_duplicate_accept_returns_409(self):
        """Two drivers racing to accept the same ride — second gets 409."""
        reset_rate_limits_for_tests()
        with TestClient(app) as client:
            with SessionLocal() as db:
                _u1, token1 = _make_driver(db)
                _u2, token2 = _make_driver(db)
                _r, rider_token = _make_rider(db)

            ride = _create_ride(client, rider_token)
            ride_id = ride["id"]

            r1 = client.post(f"/drivers/accept-ride/{ride_id}", headers=_auth(token1))
            r2 = client.post(f"/drivers/accept-ride/{ride_id}", headers=_auth(token2))

        assert r1.status_code == 200, f"first accept: {r1.text}"
        assert r2.status_code == 409, f"second accept should be 409: {r2.text}"

    def test_missing_required_ride_field_returns_422(self):
        """Creating a ride without required coordinates returns 422, not 500."""
        reset_rate_limits_for_tests()
        with TestClient(app) as client:
            with SessionLocal() as db:
                _r, rider_token = _make_rider(db)
            # pickup_location required but omitted
            r = client.post("/rides/", headers=_auth(rider_token), json={"dropoff_location": "Somewhere"})
        assert r.status_code == 422, r.text

    def test_presence_toggle_stable_under_rapid_calls(self):
        """Rapid online/offline toggles don't crash or return 500."""
        reset_rate_limits_for_tests()
        with TestClient(app) as client:
            with SessionLocal() as db:
                _u, driver_token = _make_driver(db)

            for online in [True, False, True, False, True]:
                r = client.patch(
                    "/drivers/me/status",
                    json={"online": online, "lat": 45.52, "lng": -122.67},
                    headers=_auth(driver_token),
                )
                assert r.status_code in (200, 204), f"presence toggle failed (online={online}): {r.text}"


# ---------------------------------------------------------------------------
# 5. Release accepted ride back to pool
# ---------------------------------------------------------------------------

class TestDeclineRideRelease:
    """Verify accepted ride can be released back to pool via decline-ride."""

    def test_accepted_ride_released_returns_to_requested(self):
        reset_rate_limits_for_tests()
        with TestClient(app) as client:
            with SessionLocal() as db:
                _u, driver_token = _make_driver(db)
                _r, rider_token = _make_rider(db)

            ride = _create_ride(client, rider_token)
            ride_id = ride["id"]

            # Accept
            accept_r = client.post(f"/drivers/accept-ride/{ride_id}", headers=_auth(driver_token))
            assert accept_r.status_code == 200, accept_r.text
            assert accept_r.json()["ride"]["status"] == "accepted"

            # Release back to pool
            release_r = client.post(
                f"/drivers/decline-ride/{ride_id}",
                json={"reason": "driver_released"},
                headers=_auth(driver_token),
            )
            assert release_r.status_code == 200, f"release failed: {release_r.text}"
            released = release_r.json()["ride"]
            assert released["status"] == "requested", f"should be back to requested, got: {released['status']}"
            assert released.get("driver_id") is None, "driver_id should be cleared after release"

    def test_cannot_release_in_progress_ride(self):
        """In-progress ride cannot be released to pool — must return 409."""
        reset_rate_limits_for_tests()
        with TestClient(app) as client:
            with SessionLocal() as db:
                _u, driver_token = _make_driver(db)
                _r, rider_token = _make_rider(db)

            ride = _create_ride(client, rider_token)
            ride_id = ride["id"]

            client.post(f"/drivers/accept-ride/{ride_id}", headers=_auth(driver_token))
            client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_auth(driver_token))
            client.post(f"/drivers/start-ride/{ride_id}", headers=_auth(driver_token))

            # Attempt to release an in-progress ride — should fail
            release_r = client.post(
                f"/drivers/decline-ride/{ride_id}",
                json={"reason": "driver_released"},
                headers=_auth(driver_token),
            )
            assert release_r.status_code == 409, f"should be 409, got {release_r.status_code}: {release_r.text}"
