"""Pydantic contracts for the dossier dispatch + ledger slice."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SupplyHeartbeatRequest(BaseModel):
    driver_id: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    heading: float | None = Field(default=None, ge=0, le=360)
    velocity_mps: float | None = Field(default=None, ge=0)
    device_timestamp: datetime | None = None
    vehicle_type: str = "standard"
    available_seats: int = Field(default=4, ge=1, le=12)
    has_child_seat: bool = False
    wheelchair_access: bool = False


class DemandRequestPayload(BaseModel):
    rider_id: str = Field(..., min_length=1)
    pickup_latitude: float = Field(..., ge=-90, le=90)
    pickup_longitude: float = Field(..., ge=-180, le=180)
    vehicle_type: str = "standard"
    idempotency_key: str = Field(..., min_length=8, max_length=128)


class TripCompletePayload(BaseModel):
    trip_id: str = Field(..., min_length=1)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    fare_cents: int = Field(..., gt=0)
    driver_share_cents: int = Field(..., gt=0)
    processing_fee_cents: int = Field(..., ge=0)
    platform_share_cents: int = Field(..., ge=0)


class BackendTruthResponse(BaseModel):
    trip_id: str | None = None
    current_state: str
    driver_id: str | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    status: str
    detail: str | None = None


class LedgerEntryDraft(BaseModel):
    account_id: str
    amount_cents: int = Field(..., gt=0)
    direction: Literal["DEBIT", "CREDIT"]
