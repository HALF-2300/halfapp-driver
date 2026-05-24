"""Dossier foundation spine — supply heartbeat, demand match, trip settlement.

Status labels (internal only; not shown in driver-app UI):
  - FOUNDATION
  - BACKEND-TRUTH EXPERIMENTAL SPINE
  - NOT WIRED TO MAIN APP
  - DO NOT USE AS PRIMARY APP PATH UNTIL RECONCILED

The active driver marketplace uses ``/drivers/*`` (see ``routes/drivers.py``).
Do not call these endpoints from ``driver-app`` until reconciliation in
``docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md`` is complete.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from schemas.dossier_marketplace import (
    BackendTruthResponse,
    DemandRequestPayload,
    SupplyHeartbeatRequest,
    TripCompletePayload,
)
from services.dossier_dispatch import (
    ImpossibleMovementError,
    complete_trip,
    get_trip_state,
    match_driver_for_request,
    new_trip_id,
    upsert_active_driver,
)
from services.dossier_ledger import (
    LedgerBalanceError,
    LedgerSplitError,
    build_trip_payment_entries,
    ensure_driver_wallet_account,
    execute_ledger_transaction,
    new_transaction_id,
)

# FOUNDATION | NOT WIRED TO MAIN APP | BACKEND-TRUTH EXPERIMENTAL SPINE
router = APIRouter(tags=["dossier-marketplace"])


# FOUNDATION — NOT WIRED TO MAIN APP — primary presence path is /drivers/presence
@router.post("/supply/heartbeat", response_model=BackendTruthResponse)
def supply_heartbeat(payload: SupplyHeartbeatRequest, db: Session = Depends(get_db)):
    try:
        upsert_active_driver(
            db,
            driver_id=payload.driver_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            heading=payload.heading,
            velocity_mps=payload.velocity_mps,
            device_timestamp=payload.device_timestamp,
            vehicle_type=payload.vehicle_type,
            available_seats=payload.available_seats,
            has_child_seat=payload.has_child_seat,
            wheelchair_access=payload.wheelchair_access,
        )
        db.commit()
        return BackendTruthResponse(
            status="HEARTBEAT_ACCEPTED",
            current_state="AVAILABLE",
            driver_id=payload.driver_id,
            allowed_actions=[],
        )
    except ImpossibleMovementError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transaction boundary failure") from exc


# FOUNDATION — NOT WIRED TO MAIN APP — primary demand path is POST /rides/ + open board
@router.post("/demand/request", response_model=BackendTruthResponse)
def demand_request(payload: DemandRequestPayload, db: Session = Depends(get_db)):
    trip_id = new_trip_id()
    try:
        result = match_driver_for_request(
            db,
            trip_id=trip_id,
            rider_id=payload.rider_id,
            pickup_latitude=payload.pickup_latitude,
            pickup_longitude=payload.pickup_longitude,
            vehicle_type=payload.vehicle_type,
            idempotency_key=payload.idempotency_key,
        )
        if result.get("status") == "NO_DRIVERS_AVAILABLE":
            db.commit()
            return BackendTruthResponse(
                trip_id=trip_id,
                status=result["status"],
                current_state=result["current_state"],
                allowed_actions=result["allowed_actions"],
            )

        db.commit()
        return BackendTruthResponse(
            trip_id=trip_id,
            status=result["status"],
            current_state=result["current_state"],
            driver_id=result.get("driver_id"),
            allowed_actions=result["allowed_actions"],
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transaction boundary failure") from exc


# FOUNDATION — NOT WIRED TO MAIN APP — primary complete path is POST /drivers/complete-ride/{id}
@router.post("/trip/complete", response_model=BackendTruthResponse)
def trip_complete(payload: TripCompletePayload, db: Session = Depends(get_db)):
    try:
        current_state = get_trip_state(db, payload.trip_id)
        if current_state != "DRIVER_EN_ROUTE":
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Trip is not in a completable state",
                    "current_state": current_state,
                },
            )

        driver_id = db.execute(
            text(
                """
                SELECT driver_id FROM trip_lifecycle_events
                WHERE trip_id = :trip_id AND to_state = 'DRIVER_EN_ROUTE'
                ORDER BY id DESC LIMIT 1
                """
            ),
            {"trip_id": payload.trip_id},
        ).scalar()
        if not driver_id:
            db.rollback()
            raise HTTPException(status_code=404, detail="Driver assignment not found for trip")

        ensure_driver_wallet_account(db, driver_id)
        entries = build_trip_payment_entries(
            driver_id=driver_id,
            fare_cents=payload.fare_cents,
            driver_share_cents=payload.driver_share_cents,
            processing_fee_cents=payload.processing_fee_cents,
            platform_share_cents=payload.platform_share_cents,
        )
        execute_ledger_transaction(
            db,
            transaction_id=new_transaction_id(),
            reference_key=payload.idempotency_key,
            description=f"Trip settlement for {payload.trip_id}",
            trip_id=payload.trip_id,
            entries=entries,
        )

        result = complete_trip(
            db,
            trip_id=payload.trip_id,
            idempotency_key=payload.idempotency_key,
        )
        db.commit()
        return BackendTruthResponse(
            trip_id=payload.trip_id,
            status=result["status"],
            current_state=result["current_state"],
            driver_id=driver_id,
            allowed_actions=result["allowed_actions"],
        )
    except (LedgerBalanceError, LedgerSplitError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transaction boundary failure") from exc
