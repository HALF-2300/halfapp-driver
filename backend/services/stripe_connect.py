"""Stripe Connect Express onboarding (HALFAPP_PAYMENTS_EXECUTION_02)."""

from __future__ import annotations

import os

import stripe
from sqlalchemy.orm import Session

from models.driver_stripe_account import DriverStripeAccount
from services.stripe_client import stripe_init


def connect_return_url() -> str:
    return os.getenv("STRIPE_CONNECT_RETURN_URL", "").strip()


def connect_refresh_url() -> str:
    return os.getenv("STRIPE_CONNECT_REFRESH_URL", "").strip()


def get_driver_stripe_account(db: Session, driver_id: int) -> DriverStripeAccount | None:
    return (
        db.query(DriverStripeAccount)
        .filter(DriverStripeAccount.driver_id == int(driver_id))
        .one_or_none()
    )


def get_or_create_express_account(db: Session, driver_id: int) -> DriverStripeAccount:
    row = get_driver_stripe_account(db, driver_id)
    if row is not None:
        return row

    stripe_init()
    acct = stripe.Account.create(type="express")

    row = DriverStripeAccount(
        driver_id=int(driver_id),
        stripe_account_id=acct["id"],
        charges_enabled=bool(acct.get("charges_enabled", False)),
        payouts_enabled=bool(acct.get("payouts_enabled", False)),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_account_link(stripe_account_id: str) -> str:
    return_url = connect_return_url()
    refresh_url = connect_refresh_url()
    if not return_url or not refresh_url:
        raise RuntimeError("connect_urls_missing")

    stripe_init()
    link = stripe.AccountLink.create(
        account=stripe_account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )
    return link["url"]


def refresh_account_flags(db: Session, stripe_account_id: str) -> dict:
    stripe_init()
    acct = stripe.Account.retrieve(stripe_account_id)
    row = (
        db.query(DriverStripeAccount)
        .filter(DriverStripeAccount.stripe_account_id == stripe_account_id)
        .one_or_none()
    )
    if row is not None:
        row.charges_enabled = bool(acct.get("charges_enabled", False))
        row.payouts_enabled = bool(acct.get("payouts_enabled", False))
        db.commit()
    return acct
