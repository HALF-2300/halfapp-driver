"""Settlement boundary ledger — obligations from locked ride_pricing only."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from database import SessionLocal, engine
from main import app
from models.ride import Ride
from models.ride_pricing import RidePricing
from models.settlement_entry import (
    ENTRY_TYPE_CUSTOMER_CHARGE,
    ENTRY_TYPE_DRIVER_PAYOUT,
    ENTRY_TYPE_PLATFORM_COMMISSION,
    ENTRY_TYPE_PLATFORM_REVENUE,
    ENTRY_TYPE_PLATFORM_SERVICE_FEE,
    ENTRY_TYPE_TIP_DRIVER,
    ENTRY_TYPE_CITY_LIABILITY,
    ENTRY_TYPE_TOLL_LIABILITY,
    SettlementEntry,
)
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus, RideStatus, to_storage_ride_status
from services.pricing_service import compute_financials
from services.ride_pricing import finalize_ride_pricing, quote_ride_pricing
from services.ride_settlement import (
    SettlementGenerationError,
    generate_settlement_entries,
    list_settlement_entries,
    settlement_already_generated,
)


def _driver_token(db, prefix: str = "settle") -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix} Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status="approved",
    )
    user.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _rider_token(db, prefix: str = "settle_r") -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix} Rider",
        "pw12345",
        UserRole.CUSTOMER,
        None,
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def test_migration_creates_settlement_entries_table():
    inspector = inspect(engine)
    assert "settlement_entries" in inspector.get_table_names()


def test_normal_25_dollar_ride_settlement_amounts():
    b = compute_financials(driver_shareable_ride_fare_cents=2500, platform_service_fee_cents=150)
    db = SessionLocal()
    try:
        ride = Ride(
            customer_name="Settle",
            status=to_storage_ride_status(RideStatus.COMPLETED),
            distance=5.0,
            duration=12,
        )
        db.add(ride)
        db.flush()
        row = RidePricing(ride_id=ride.id)
        row.driver_shareable_fare_cents = b.driver_shareable_ride_fare_cents
        row.platform_service_fee_cents = b.platform_service_fee_cents
        row.platform_commission_cents = b.platform_commission_cents
        row.driver_ride_payout_cents = b.driver_ride_payout_cents
        row.driver_commission_cents = b.driver_ride_payout_cents
        row.driver_earnings_cents = b.driver_total_payout_cents
        row.platform_revenue_cents = b.platform_revenue_cents
        row.platform_earnings_cents = b.platform_revenue_cents
        row.customer_total_cents = b.customer_total_cents
        row.total_rider_charge_cents = b.customer_total_cents
        row.financial_locked = True
        db.add(row)
        db.commit()

        entries = generate_settlement_entries(db, ride_id=ride.id)
        db.commit()
        by_type = {e.entry_type: e for e in entries}
        assert by_type[ENTRY_TYPE_PLATFORM_COMMISSION].amount_cents == 500
        assert by_type[ENTRY_TYPE_PLATFORM_SERVICE_FEE].amount_cents == 150
        assert by_type[ENTRY_TYPE_PLATFORM_REVENUE].amount_cents == 650
        assert by_type[ENTRY_TYPE_DRIVER_PAYOUT].amount_cents == 2000
        assert by_type[ENTRY_TYPE_CUSTOMER_CHARGE].amount_cents == 2650
    finally:
        db.close()


def test_tip_goes_to_driver_not_commission():
    b = compute_financials(driver_shareable_ride_fare_cents=2500, tip_cents=500)
    db = SessionLocal()
    try:
        ride = Ride(customer_name="Tip", status="completed")
        db.add(ride)
        db.flush()
        row = RidePricing(ride_id=ride.id)
        row.driver_shareable_fare_cents = 2500
        row.platform_service_fee_cents = 150
        row.platform_commission_cents = b.platform_commission_cents
        row.driver_ride_payout_cents = 2000
        row.driver_earnings_cents = b.driver_total_payout_cents
        row.platform_revenue_cents = b.platform_revenue_cents
        row.customer_total_cents = b.customer_total_cents
        row.tip_cents = 500
        row.financial_locked = True
        db.add(row)
        db.commit()

        entries = generate_settlement_entries(db, ride_id=ride.id)
        by_type = {e.entry_type: e for e in entries}
        assert by_type[ENTRY_TYPE_PLATFORM_COMMISSION].amount_cents == 500
        assert by_type[ENTRY_TYPE_TIP_DRIVER].amount_cents == 500
        assert by_type[ENTRY_TYPE_DRIVER_PAYOUT].amount_cents == 2000
    finally:
        db.close()


def test_pass_through_fees_are_liabilities_not_platform_revenue():
    b = compute_financials(
        driver_shareable_ride_fare_cents=2500,
        city_fee_cents=300,
        airport_fee_cents=200,
        toll_cents=100,
        accessibility_fee_cents=50,
    )
    db = SessionLocal()
    try:
        ride = Ride(customer_name="Pass", status="completed")
        db.add(ride)
        db.flush()
        row = RidePricing(ride_id=ride.id)
        row.driver_shareable_fare_cents = 2500
        row.platform_service_fee_cents = 150
        row.platform_commission_cents = 500
        row.driver_ride_payout_cents = 2000
        row.driver_earnings_cents = 2000
        row.platform_revenue_cents = 650
        row.customer_total_cents = b.customer_total_cents
        row.city_fee_cents = 300
        row.airport_fee_cents = 200
        row.toll_cents = 100
        row.accessibility_fee_cents = 50
        row.financial_locked = True
        db.add(row)
        db.commit()

        entries = generate_settlement_entries(db, ride_id=ride.id)
        by_type = {e.entry_type: e for e in entries}
        assert by_type[ENTRY_TYPE_PLATFORM_REVENUE].amount_cents == 650
        assert by_type[ENTRY_TYPE_CITY_LIABILITY].amount_cents == 300
        assert by_type[ENTRY_TYPE_TOLL_LIABILITY].amount_cents == 100
        assert ENTRY_TYPE_DRIVER_PAYOUT in by_type
        assert by_type[ENTRY_TYPE_DRIVER_PAYOUT].amount_cents == 2000
    finally:
        db.close()


def test_cancelled_ride_does_not_generate_settlement():
    db = SessionLocal()
    try:
        ride = Ride(customer_name="Cancel", status=to_storage_ride_status(RideStatus.CANCELLED))
        db.add(ride)
        db.flush()
        pricing = RidePricing(ride_id=ride.id, financial_locked=True, driver_shareable_fare_cents=2500)
        db.add(pricing)
        db.commit()
        with pytest.raises(SettlementGenerationError):
            generate_settlement_entries(db, ride_id=ride.id)
    finally:
        db.close()


def test_idempotent_generation_no_duplicates():
    db = SessionLocal()
    try:
        ride = Ride(customer_name="Idem", status="completed")
        db.add(ride)
        db.flush()
        pricing = RidePricing(
            ride_id=ride.id,
            financial_locked=True,
            driver_shareable_fare_cents=2500,
            platform_service_fee_cents=150,
            platform_commission_cents=500,
            driver_ride_payout_cents=2000,
            driver_earnings_cents=2000,
            platform_revenue_cents=650,
            customer_total_cents=2650,
        )
        db.add(pricing)
        db.commit()

        first = generate_settlement_entries(db, ride_id=ride.id)
        db.commit()
        second = generate_settlement_entries(db, ride_id=ride.id)
        assert len(first) == len(second)
        assert settlement_already_generated(db, ride_id=ride.id)
        assert len(list_settlement_entries(db, ride_id=ride.id)) == len(first)
    finally:
        db.close()


def test_locked_settlement_row_cannot_duplicate_entry_type():
    db = SessionLocal()
    try:
        ride = Ride(customer_name="Lock", status="completed")
        db.add(ride)
        db.flush()
        pricing = RidePricing(
            ride_id=ride.id,
            financial_locked=True,
            driver_shareable_fare_cents=2500,
            platform_service_fee_cents=150,
            platform_commission_cents=500,
            driver_ride_payout_cents=2000,
            driver_earnings_cents=2000,
            platform_revenue_cents=650,
            customer_total_cents=2650,
        )
        db.add(pricing)
        db.commit()
        generate_settlement_entries(db, ride_id=ride.id)
        db.commit()

        dup = SettlementEntry(
            ride_id=ride.id,
            pricing_id=ride.id,
            settlement_status="ready",
            entry_type=ENTRY_TYPE_DRIVER_PAYOUT,
            party="driver",
            amount_cents=9999,
            entry_checksum="deadbeef",
            source="ride_pricing_locked",
        )
        db.add(dup)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_completed_ride_via_api_creates_settlement():
    db = SessionLocal()
    try:
        rider_token = _rider_token(db)
        driver_token = _driver_token(db)
    finally:
        db.close()

    with TestClient(app) as client:
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "pickup_location": "Settle A",
                "dropoff_location": "Settle B",
                "pickup_latitude": 45.501,
                "pickup_longitude": -122.681,
                "dropoff_latitude": 45.551,
                "dropoff_longitude": -122.611,
            },
        )
        assert created.status_code == 200, created.text
        ride_id = created.json()["ride"]["id"]
        headers = {"Authorization": f"Bearer {driver_token}"}
        client.put("/drivers/presence", headers=headers, json={"state": "available"})
        client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)
        client.post(f"/drivers/arrive-pickup/{ride_id}", headers=headers)
        client.post(f"/drivers/start-ride/{ride_id}", headers=headers)
        done = client.post(
            f"/drivers/complete-ride/{ride_id}",
            headers=headers,
            json={"tip_cents": 500},
        )
        assert done.status_code == 200, done.text

        settlement = client.get(f"/drivers/rides/{ride_id}/settlement", headers=headers)
        assert settlement.status_code == 200, settlement.text
        body = settlement.json()
        assert body["settlement_status"] == "ready"
        assert len(body["entries"]) >= 5
        types = {e["entry_type"] for e in body["entries"]}
        assert ENTRY_TYPE_CUSTOMER_CHARGE in types
        assert ENTRY_TYPE_DRIVER_PAYOUT in types
        assert ENTRY_TYPE_TIP_DRIVER in types

        db2 = SessionLocal()
        try:
            again = generate_settlement_entries(db2, ride_id=ride_id)
            assert len(again) == len(body["entries"])
        finally:
            db2.close()


def test_settlement_endpoint_requires_driver_access():
    db = SessionLocal()
    try:
        rider_token = _rider_token(db, "acc_r")
        driver_a = _driver_token(db, "acc_a")
        driver_b = _driver_token(db, "acc_b")
    finally:
        db.close()

    with TestClient(app) as client:
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "pickup_location": "Acc A",
                "dropoff_location": "Acc B",
                "pickup_latitude": 45.501,
                "pickup_longitude": -122.681,
                "dropoff_latitude": 45.551,
                "dropoff_longitude": -122.611,
            },
        )
        ride_id = created.json()["ride"]["id"]
        blocked = client.get(
            f"/drivers/rides/{ride_id}/settlement",
            headers={"Authorization": f"Bearer {driver_b}"},
        )
        assert blocked.status_code == 403
