"""ORM models for the dossier dispatch + double-entry ledger slice."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, DateTime, Float, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class ActiveDriver(Base):
    __tablename__ = "active_drivers"

    id = Column(String, primary_key=True)
    status = Column(String, nullable=False, default="OFFLINE")
    vehicle_type = Column(String, nullable=False, default="standard")
    latitude = Column(Float)
    longitude = Column(Float)
    heading = Column(Float)
    velocity_mps = Column(Float)
    device_timestamp = Column(DateTime)
    location_updated_at = Column(DateTime)
    available_seats = Column(Integer, nullable=False, default=4)
    has_child_seat = Column(Integer, nullable=False, default=0)
    wheelchair_access = Column(Integer, nullable=False, default=0)
    assigned_trip_id = Column(String)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
    updated_at = Column(DateTime, nullable=False, default=utc_now_naive)


class TripLifecycleEvent(Base):
    __tablename__ = "trip_lifecycle_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(String, nullable=False)
    rider_id = Column(String)
    driver_id = Column(String)
    from_state = Column(String)
    to_state = Column(String, nullable=False)
    trigger_event = Column(String, nullable=False)
    idempotency_key = Column(String, unique=True)
    payload_json = Column(Text, nullable=False, default="{}")
    occurred_at = Column(DateTime, nullable=False, default=utc_now_naive)


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"
    __table_args__ = (
        CheckConstraint("normality IN ('DEBIT', 'CREDIT')", name="ck_ledger_accounts_normality"),
    )

    id = Column(String, primary_key=True)
    user_id = Column(String)
    account_type = Column(String, nullable=False)
    normality = Column(String, nullable=False)
    label = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id = Column(String, primary_key=True)
    reference_key = Column(String, unique=True)
    description = Column(String, nullable=False, default="")
    trip_id = Column(String)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_ledger_entries_amount_positive"),
        CheckConstraint("direction IN ('DEBIT', 'CREDIT')", name="ck_ledger_entries_direction"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String, nullable=False)
    account_id = Column(String, nullable=False)
    amount_cents = Column(Integer, nullable=False)
    direction = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
