"""Seed backend-owned data for the HalfApp investor showcase.

This script uses the existing schema only. It does not create migrations,
does not create UI fixtures, and does not seed payments, ETA, or ranking claims.
Run from the repository root:

    python backend/scripts/seed_investor_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal, engine  # noqa: E402
from models.presence import DriverPresence  # noqa: E402
from models.ride import Ride  # noqa: E402
from models.user import User, UserRole  # noqa: E402
from services.auth import create_user, get_user_by_email  # noqa: E402
from services.datetime_utils import utc_now_naive  # noqa: E402

DRIVER_EMAIL = "investor.driver@halfapp.demo"
DRIVER_PASSWORD = "InvestorDemo123!"
RIDER_EMAIL = "investor.rider@halfapp.demo"
RIDER_PASSWORD = "InvestorDemo123!"


def require_existing_tables() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    required_tables = {"users", "rides", "driver_presence"}
    missing = sorted(required_tables - existing_tables)
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(
            f"Cannot seed investor demo data. Missing existing tables: {joined}. "
            "Run the normal backend migration/setup flow first."
        )


def ensure_driver(db) -> User:
    driver = get_user_by_email(db, DRIVER_EMAIL)
    if driver:
        driver.name = "Investor Demo Driver"
        driver.role = UserRole.DRIVER
        driver.license_no = driver.license_no or "HALFAPP-INVESTOR-DRIVER"
        driver.availability = "available"
        return driver

    return create_user(
        db,
        email=DRIVER_EMAIL,
        name="Investor Demo Driver",
        password=DRIVER_PASSWORD,
        role=UserRole.DRIVER,
        license_no="HALFAPP-INVESTOR-DRIVER",
    )


def ensure_rider(db) -> User:
    rider = get_user_by_email(db, RIDER_EMAIL)
    if rider:
        rider.name = "Investor Demo Rider"
        rider.role = UserRole.CUSTOMER
        return rider

    return create_user(
        db,
        email=RIDER_EMAIL,
        name="Investor Demo Rider",
        password=RIDER_PASSWORD,
        role=UserRole.CUSTOMER,
    )


def ensure_presence(db, driver: User) -> DriverPresence:
    presence = db.query(DriverPresence).filter(DriverPresence.driver_id == driver.id).first()
    now = utc_now_naive()
    if not presence:
        presence = DriverPresence(driver_id=driver.id)
        db.add(presence)

    presence.requested_state = "available"
    presence.effective_state = "available"
    presence.state_changed_at = now
    presence.heartbeat_at = now
    presence.stale_reason = None
    presence.updated_at = now
    driver.availability = "available"
    return presence


def seed_requested_rides(db, rider: User) -> list[Ride]:
    existing = (
        db.query(Ride)
        .filter(Ride.customer_id == rider.id, Ride.lifecycle_reason == "investor_showcase_seed")
        .all()
    )
    if existing:
        for ride in existing:
            if ride.status not in {"accepted", "driver_arrived", "in_progress", "completed"}:
                ride.status = "requested"
                ride.driver_id = None
        return existing

    rides = [
        Ride(
            customer_id=rider.id,
            customer_name="Operator Account - Downtown Pickup",
            status="requested",
            pickup_location="Downtown Operations Hub",
            destination="Northside Fleet Drop",
            pickup_latitude=45.523064,
            pickup_longitude=-122.676483,
            dropoff_latitude=45.55202,
            dropoff_longitude=-122.68192,
            fare_amount=18.75,
            distance=8.4,
            duration=19,
            lifecycle_reason="investor_showcase_seed",
        ),
        Ride(
            customer_id=rider.id,
            customer_name="Local Business Dispatch",
            status="requested",
            pickup_location="Warehouse Gate B",
            destination="South Market Receiving",
            pickup_latitude=45.51531,
            pickup_longitude=-122.67842,
            dropoff_latitude=45.49891,
            dropoff_longitude=-122.66911,
            fare_amount=24.50,
            distance=11.2,
            duration=27,
            lifecycle_reason="investor_showcase_seed",
        ),
    ]
    db.add_all(rides)
    return rides


def main() -> None:
    require_existing_tables()
    db = SessionLocal()
    try:
        driver = ensure_driver(db)
        rider = ensure_rider(db)
        ensure_presence(db, driver)
        rides = seed_requested_rides(db, rider)
        db.commit()
        print("Investor showcase backend seed complete.")
        print(f"Driver login: {DRIVER_EMAIL} / {DRIVER_PASSWORD}")
        print(f"Driver id: {driver.id}")
        print(f"Seeded backend requested rides: {len(rides)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

