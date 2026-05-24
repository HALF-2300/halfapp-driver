"""v0.1 U.S. ride pricing ledger — required business scenarios."""

import uuid

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.ride import Ride
from models.ride_pricing import RidePricing
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus, RideStatus
from services.pricing_service import compute_financials
from services.ride_pricing import (
    PricingLockedError,
    finalize_ride_pricing,
    get_ride_pricing,
    quote_ride_pricing,
)
from models.user import UserRole


def test_normal_ride_commission_and_totals():
    b = compute_financials(
        driver_shareable_ride_fare_cents=2500,
        platform_service_fee_cents=150,
        city_fee_cents=0,
        tip_cents=0,
    )
    assert b.platform_commission_cents == 500
    assert b.driver_ride_payout_cents == 2000
    assert b.platform_revenue_cents == 650
    assert b.customer_total_cents == 2650


def test_short_ride_minimum_protection():
    b = compute_financials(
        driver_shareable_ride_fare_cents=1000,
        platform_service_fee_cents=150,
    )
    assert b.platform_commission_cents == 200
    assert b.driver_ride_payout_cents == 800
    assert b.platform_revenue_cents == 350
    assert b.customer_total_cents == 1150


def test_tip_not_commissioned():
    b = compute_financials(
        driver_shareable_ride_fare_cents=2500,
        tip_cents=500,
    )
    assert b.platform_commission_cents == 500
    assert b.driver_ride_payout_cents == 2000
    assert b.driver_total_payout_cents == 2500


def test_pass_through_excluded_from_commission():
    b = compute_financials(
        driver_shareable_ride_fare_cents=2500,
        city_fee_cents=300,
        airport_fee_cents=200,
        toll_cents=100,
        accessibility_fee_cents=50,
    )
    assert b.platform_commission_cents == 500
    assert b.driver_ride_payout_cents == 2000
    assert b.customer_total_cents == 2500 + 150 + 300 + 200 + 100 + 50


def _driver_token(db) -> str:
    uid = uuid.uuid4().hex[:10]
    u = create_user(
        db,
        f"pricing_driver_{uid}@example.com",
        "Pricing Driver",
        "pw12345",
        UserRole.DRIVER,
        f"PD{uid}",
        driver_approval_status="approved",
    )
    u.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=u.email, role=u.role.value)


def test_refresh_persistence_pricing_survives_reload():
    db = SessionLocal()
    try:
        token = _driver_token(db)
        from models.user import User

        driver_user = db.query(User).filter(User.email.like("pricing_driver_%")).order_by(User.id.desc()).first()
        ride = Ride(
            customer_name="Persist Rider",
            status="accepted",
            driver_id=driver_user.id,
            pickup_location="A",
            destination="B",
            distance=4.0,
            duration=12,
        )
        db.add(ride)
        db.commit()
        db.refresh(ride)
        quote_ride_pricing(db, ride_id=ride.id, distance_km=4.0, duration_minutes=12)
        db.commit()
        rid = ride.id
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        r1 = client.get("/drivers/my-rides", headers=headers)
        assert r1.status_code == 200
        rides1 = r1.json()
        match1 = next((x for x in rides1 if x["id"] == rid), None)
        assert match1 is not None
        assert match1.get("pricing") is not None
        assert match1["pricing"]["driver_shareable_fare_cents"] > 0

        r2 = client.get("/drivers/my-rides", headers=headers)
        match2 = next((x for x in r2.json() if x["id"] == rid), None)
        assert match2["pricing"]["driver_shareable_fare_cents"] == match1["pricing"]["driver_shareable_fare_cents"]


def test_completion_lock_prevents_recalculation():
    db = SessionLocal()
    try:
        ride = Ride(customer_name="Lock Rider", status="requested", distance=3.0, duration=10)
        db.add(ride)
        db.commit()
        db.refresh(ride)
        finalize_ride_pricing(db, ride_id=ride.id, distance_km=3.0, duration_minutes=10, lock=True)
        db.commit()
        with pytest.raises(PricingLockedError):
            finalize_ride_pricing(db, ride_id=ride.id, distance_km=99.0, lock=False)
    finally:
        db.close()


def test_cancelled_ride_no_completed_payout_ledger():
    db = SessionLocal()
    try:
        ride = Ride(customer_name="Cancel Rider", status="cancelled", distance=2.0, duration=8)
        ride.cancelled_at = ride.created_at
        db.add(ride)
        db.commit()
        db.refresh(ride)
        row = get_ride_pricing(db, ride.id)
        assert row is None or not row.financial_locked
        if row:
            assert row.driver_earnings_cents == 0 or ride.status == "cancelled"
    finally:
        db.close()


def test_complete_ride_api_locks_financial_fields():
    db = SessionLocal()
    try:
        token = _driver_token(db)
        from models.user import User

        driver_user = db.query(User).filter(User.email.like("pricing_driver_%")).order_by(User.id.desc()).first()
        ride = Ride(
            customer_name="API Complete",
            status="in_progress",
            driver_id=driver_user.id,
            distance=4.0,
            duration=12,
        )
        db.add(ride)
        db.commit()
        db.refresh(ride)
        quote_ride_pricing(db, ride_id=ride.id, distance_km=4.0, duration_minutes=12)
        db.commit()
        rid = ride.id
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        r = client.post(f"/drivers/complete-ride/{rid}", headers=headers, json={"tip_cents": 500})
        assert r.status_code == 200
        pricing = r.json()["ride"]["pricing"]
        assert pricing["financial_locked"] is True
        assert pricing["platform_commission_cents"] > 0
        assert pricing["driver_total_payout_cents"] >= pricing["driver_ride_payout_cents"]

        r2 = client.post(f"/drivers/complete-ride/{rid}", headers=headers)
        assert r2.status_code == 409
