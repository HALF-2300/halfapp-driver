"""Driver Stripe Connect onboarding routes (HALFAPP_PAYMENTS_EXECUTION_02)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.rbac import AuthPrincipal, load_principal_user, require_role
from services.stripe_client import payouts_enabled, stripe_enabled
from services.stripe_connect import get_driver_stripe_account
from services.stripe_connect import (
    create_account_link,
    get_or_create_express_account,
    refresh_account_flags,
)

router = APIRouter(prefix="/drivers/stripe", tags=["drivers-stripe"])
DRIVER_ACCESS = require_role("driver")


@router.get("/connect/status")
def connect_status(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """Read-only Connect account flags from DB (no Stripe API call)."""
    driver_user = load_principal_user(db, driver_user)
    if driver_user.id is None:
        raise HTTPException(status_code=401, detail="user_not_found")

    payments_on = stripe_enabled()
    payouts_on = payouts_enabled()
    row = get_driver_stripe_account(db, driver_user.id) if payments_on else None

    if row is None:
        return {
            "payments_enabled": payments_on,
            "payouts_enabled_flag": payouts_on,
            "has_connect_account": False,
            "stripe_account_id": None,
            "charges_enabled": False,
            "provider_payouts_enabled": False,
        }

    return {
        "payments_enabled": payments_on,
        "payouts_enabled_flag": payouts_on,
        "has_connect_account": True,
        "stripe_account_id": row.stripe_account_id,
        "charges_enabled": bool(row.charges_enabled),
        "provider_payouts_enabled": bool(row.payouts_enabled),
    }


@router.post("/connect/start")
def connect_start(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    if not stripe_enabled():
        raise HTTPException(status_code=409, detail="payments_disabled")

    driver_user = load_principal_user(db, driver_user)
    if driver_user.id is None:
        raise HTTPException(status_code=401, detail="user_not_found")

    try:
        row = get_or_create_express_account(db, driver_user.id)
        url = create_account_link(row.stripe_account_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"onboarding_url": url, "stripe_account_id": row.stripe_account_id}


@router.post("/connect/refresh")
def connect_refresh(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    if not stripe_enabled():
        raise HTTPException(status_code=409, detail="payments_disabled")

    driver_user = load_principal_user(db, driver_user)
    if driver_user.id is None:
        raise HTTPException(status_code=401, detail="user_not_found")

    row = get_or_create_express_account(db, driver_user.id)
    acct = refresh_account_flags(db, row.stripe_account_id)
    return {
        "charges_enabled": bool(acct.get("charges_enabled", False)),
        "payouts_enabled": bool(acct.get("payouts_enabled", False)),
        "stripe_account_id": row.stripe_account_id,
    }
