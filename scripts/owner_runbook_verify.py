#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# Force UTF-8 stdout/stderr on Windows to avoid charmap errors with Unicode
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def http(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = Request(f"{API}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as res:
            raw = res.read().decode()
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"{method} {path} -> {exc.code}: {detail}") from exc


def _approve_driver_in_db(driver_email: str) -> tuple[int, str]:
    from database import SessionLocal
    from models.user import User, UserRole
    from models.driver_approval import DriverApprovalStatus
    from services.auth import create_access_token
    from services.driver_approval import set_driver_approval

    db = SessionLocal()
    try:
        driver = db.query(User).filter(User.email == driver_email).first()
        if not driver:
            raise RuntimeError(f"driver {driver_email} not in DB")
        admin = (
            db.query(User)
            .filter(User.role == UserRole.ADMIN)
            .order_by(User.id.asc())
            .first()
        )
        if not admin:
            from services.auth import create_user

            uid = uuid.uuid4().hex[:6]
            admin = create_user(
                db,
                f"runbook_admin_{uid}@local.test",
                "Runbook Admin",
                "RunbookAdmin1!",
                UserRole.ADMIN,
            )
            db.commit()
        set_driver_approval(
            db,
            driver_id=driver.id,
            status=DriverApprovalStatus.APPROVED,
            reason="owner_runbook_verify",
            reviewed_by=admin.id,
        )
        db.commit()
        return driver.id, create_access_token(sub=admin.email, role=admin.role.value)
    finally:
        db.close()


def main() -> int:
    stamp = uuid.uuid4().hex[:8]
    print(f"Owner runbook verify @ {API}")

    health = http("GET", "/health")
    assert health.get("status") == "ok", health
    print("  [ok] GET /health")

    rider_email = f"owner_rider_{stamp}@example.com"
    driver_email = f"owner_driver_{stamp}@example.com"
    password_r = "OwnerRider1!"
    password_d = "OwnerDriver1!"

    http(
        "POST",
        "/auth/rider/register",
        {"email": rider_email, "name": "Owner Rider", "password": password_r},
    )
    rider_token = http("POST", "/auth/rider/login", {"email": rider_email, "password": password_r})[
        "access_token"
    ]
    print("  [ok] rider register + login")

    http(
        "POST",
        "/auth/register",
        {
            "email": driver_email,
            "name": "Owner Driver",
            "password": password_d,
            "role": "driver",
            "license_no": f"OWN{stamp}",
        },
    )
    driver_id, admin_token = _approve_driver_in_db(driver_email)
    driver_token = http("POST", "/auth/login", {"email": driver_email, "password": password_d})[
        "access_token"
    ]
    print("  [ok] driver register + DB approval + login")

    http(
        "PUT",
        "/drivers/profile",
        {
            "vehicle_make": "Toyota",
            "vehicle_model": "Prius",
            "vehicle_year": 2020,
            "license_plate": f"OWN{stamp[:4]}",
            "insurance_policy": f"INS-{stamp}",
        },
        token=driver_token,
    )
    print("  [ok] driver submitted vehicle + insurance policy")

    http(
        "PATCH",
        f"/admin/drivers/{driver_id}/readiness",
        {
            "insurance_expires_at": "2027-05-25T00:00:00Z",
            "vehicle_ready": True,
            "reason": "owner_runbook_verify",
        },
        token=admin_token,
    )
    print("  [ok] ops reviewed vehicle + insurance expiry readiness")

    http(
        "PATCH",
        "/drivers/me/status",
        {"online": True, "lat": 45.5152, "lng": -122.6784},
        token=driver_token,
    )
    http("PUT", "/drivers/presence", {"state": "available"}, token=driver_token)
    http("POST", "/drivers/heartbeat", None, token=driver_token)
    print("  [ok] driver online + presence")

    created = http(
        "POST",
        "/rides/",
        {
            "customer_name": "Owner Rider",
            "pickup_location": "Pioneer Courthouse Square, Portland",
            "dropoff_location": "Portland International Airport",
            "pickup_latitude": 45.5189,
            "pickup_longitude": -122.6793,
            "dropoff_latitude": 45.5898,
            "dropoff_longitude": -122.5951,
        },
        token=rider_token,
    )
    ride_id = created["ride"]["id"]
    assert created["ride"]["status"] == "requested"
    print(f"  [ok] POST /rides/ -> ride #{ride_id}")

    estimate = http(
        "POST",
        "/rides/estimate",
        {
            "pickup_latitude": 45.5189,
            "pickup_longitude": -122.6793,
            "dropoff_latitude": 45.5898,
            "dropoff_longitude": -122.5951,
        },
        token=rider_token,
    )
    assert estimate.get("amount_cents", 0) > 0
    print(f"  [ok] fare estimate ${estimate['amount_cents'] / 100:.2f}")

    available = http("GET", "/drivers/available-rides", token=driver_token)
    assert any(r["id"] == ride_id for r in available)
    print("  [ok] driver sees ride on open board")

    for path in [
        f"/drivers/accept-ride/{ride_id}",
        f"/drivers/arrive-pickup/{ride_id}",
        f"/drivers/start-ride/{ride_id}",
    ]:
        http("POST", path, {}, token=driver_token)

    http(
        "POST",
        f"/drivers/complete-ride/{ride_id}",
        {"tip_cents": 200, "toll_cents": 0, "city_fee_cents": 0},
        token=driver_token,
    )
    print("  [ok] driver accept → arrive → start → complete")

    ride = http("GET", f"/rides/{ride_id}", token=rider_token)["ride"]
    assert ride["status"] == "completed"
    assert ride.get("assigned_driver_name") == "Owner Driver"
    print("  [ok] rider GET ride -> completed + driver name")

    payment = http("GET", f"/rides/{ride_id}/payment", token=rider_token)
    assert payment["payment"]["status"] in {"captured", "authorized", "pending"}
    print(f"  [ok] rider payment -> {payment['payment']['status']}")

    history = http("GET", "/rides/my-rides", token=rider_token)
    assert any(r["id"] == ride_id for r in history["rides"])
    print("  [ok] GET /rides/my-rides")

    earnings = http("GET", "/drivers/me/ride-payments", token=driver_token)
    assert earnings.get("payments") is not None
    print("  [ok] driver ride-payments")

    print("\nRUNBOOK API PASS")
    print("Human sign-off: open http://127.0.0.1:3023 + http://127.0.0.1:3022 and repeat once in the UI.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nRUNBOOK API FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
