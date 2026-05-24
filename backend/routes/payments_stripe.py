"""Stripe PaymentIntent helpers on payment_execution rows (HALFAPP_PAYMENTS_EXECUTION_02)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.ride import Ride
from services.payment_execution import (
    create_charge_intent_from_pricing,
    get_charge_execution_for_ride,
    start_stripe_destination_payment_intent,
)
from services.rbac import AuthPrincipal, load_principal_user, require_role
from services.stripe_client import stripe_enabled

router = APIRouter(prefix="/payments/stripe", tags=["payments-stripe"])
DRIVER_ACCESS = require_role("driver")


@router.post("/rides/{ride_id}/payment-intent")
def create_payment_intent_for_ride(
    ride_id: int,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    if not stripe_enabled():
        raise HTTPException(status_code=409, detail="payments_disabled")

    driver_user = load_principal_user(db, driver_user)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id != driver_user.id:
        raise HTTPException(status_code=404, detail="Ride not found or not assigned to you")

    try:
        execution = get_charge_execution_for_ride(db, ride_id) or create_charge_intent_from_pricing(
            db, ride_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    execution, client_secret = start_stripe_destination_payment_intent(
        db, execution, int(ride.driver_id)
    )
    db.commit()

    return {
        "payment_execution_id": execution.id,
        "status": execution.status,
        "stripe_payment_intent_id": execution.external_id,
        "client_secret": client_secret,
    }
