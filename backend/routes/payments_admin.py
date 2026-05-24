"""Admin payment operations — refunds (HALFAPP_PAYMENTS_EXECUTION_02_5 / 03)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.payment_execution import EXECUTION_TYPE_CHARGE_RIDER, PaymentExecution
from services.payment_execution import (
    create_refund_execution,
    execute_stripe_refund,
    get_charge_execution_for_ride,
)
from services.rbac import AuthPrincipal, require_role
from services.stripe_client import stripe_enabled

router = APIRouter(prefix="/payments/admin", tags=["payments-admin"])
ADMIN_ACCESS = require_role("admin")


class RefundIn(BaseModel):
    amount_cents: int | None = Field(
        default=None,
        ge=1,
        description="Partial refund in cents; omit for full remaining-refundable amount",
    )


@router.post("/rides/{ride_id}/refund")
def refund_ride(
    ride_id: int,
    payload: RefundIn,
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    if not stripe_enabled():
        raise HTTPException(status_code=409, detail="payments_disabled")

    charge = get_charge_execution_for_ride(db, ride_id)
    if charge is None:
        charge = (
            db.query(PaymentExecution)
            .filter(
                PaymentExecution.ride_id == ride_id,
                PaymentExecution.execution_type == EXECUTION_TYPE_CHARGE_RIDER,
            )
            .one_or_none()
        )
    if charge is None:
        raise HTTPException(status_code=404, detail="charge_not_found")

    try:
        refund = create_refund_execution(db, charge, amount_cents=payload.amount_cents)
        refund = execute_stripe_refund(db, refund, charge)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    return {
        "refund_execution_id": refund.id,
        "amount_cents": refund.amount_cents,
        "status": refund.status,
        "stripe_refund_id": refund.external_id,
    }
