"""Stripe signed webhooks (HALFAPP_PAYMENTS_EXECUTION_02 / 02_5 / 03 / 05)."""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models.payment_execution import (
    EXECUTION_TYPE_CHARGE_RIDER,
    EXTERNAL_PROVIDER_STRIPE,
    PaymentExecution,
)
from services.datetime_utils import utc_now_naive
from services.payment_events import record_event_once
from services.payment_execution import upsert_dispute_execution
from services.stripe_client import (
    default_currency,
    payouts_enabled,
    stripe_connect_webhook_secret,
    stripe_enabled,
    stripe_init,
    stripe_webhook_secret,
)
from services.stripe_payout_ingest import (
    ingest_payout,
    map_payout_to_transfers_via_balance_transactions,
)
from services.stripe_transfer_ingest import ingest_transfer

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


def _construct_event(payload: bytes, sig: str) -> tuple[dict, str]:
    """
    Verify webhook signature. Returns (event, verified_via) where verified_via is
    'platform' or 'connect' depending on which secret matched.
    """
    candidates: list[tuple[str, str]] = []
    platform = stripe_webhook_secret()
    connect = stripe_connect_webhook_secret()
    if platform:
        candidates.append(("platform", platform))
    if connect:
        candidates.append(("connect", connect))
    if not candidates:
        raise RuntimeError("webhook_secret_missing")

    last_exc: Exception | None = None
    for verified_via, secret in candidates:
        try:
            event = stripe.Webhook.construct_event(payload, sig, secret)
            return event, verified_via
        except stripe.error.SignatureVerificationError as exc:
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("webhook_secret_missing")


def _update_execution_status(db: Session, external_id: str, status: str) -> int | None:
    row = (
        db.query(PaymentExecution)
        .filter(
            PaymentExecution.external_provider == EXTERNAL_PROVIDER_STRIPE,
            PaymentExecution.external_id == external_id,
        )
        .one_or_none()
    )
    if row is None:
        return None
    row.status = str(status)
    row.updated_at = utc_now_naive()
    return row.id


def _charge_for_payment_intent(db: Session, payment_intent_id: str | None) -> PaymentExecution | None:
    if not payment_intent_id:
        return None
    return (
        db.query(PaymentExecution)
        .filter(
            PaymentExecution.external_provider == EXTERNAL_PROVIDER_STRIPE,
            PaymentExecution.external_id == payment_intent_id,
            PaymentExecution.execution_type == EXECUTION_TYPE_CHARGE_RIDER,
        )
        .one_or_none()
    )


def _charge_id_from_payment_intent(obj: dict) -> str | None:
    charges = obj.get("charges")
    if isinstance(charges, dict):
        data = charges.get("data") or []
        if data and isinstance(data[0], dict):
            charge_id = data[0].get("id")
            if charge_id:
                return str(charge_id)
    latest = obj.get("latest_charge")
    if isinstance(latest, str) and latest.startswith("ch_"):
        return latest
    if isinstance(latest, dict) and latest.get("id"):
        return str(latest["id"])
    return None


def _link_charge_execution(db: Session, payment_intent_id: str, obj: dict) -> int | None:
    row = _charge_for_payment_intent(db, payment_intent_id)
    if row is None:
        return None
    status = obj.get("status")
    if status:
        row.status = str(status)
    charge_id = _charge_id_from_payment_intent(obj)
    if charge_id:
        row.external_charge_id = charge_id
    row.updated_at = utc_now_naive()
    return row.id


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    if not stripe_enabled():
        raise HTTPException(status_code=404, detail="not_found")

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="missing_signature")

    if not stripe_webhook_secret() and not stripe_connect_webhook_secret():
        raise HTTPException(status_code=500, detail="webhook_secret_missing")

    stripe_init()
    payload = await request.body()

    try:
        event, verified_via = _construct_event(payload, stripe_signature)
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="invalid_signature") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bad_request") from exc
    except RuntimeError as exc:
        if "webhook_secret_missing" in str(exc):
            raise HTTPException(status_code=500, detail="webhook_secret_missing") from exc
        raise HTTPException(status_code=400, detail="bad_request") from exc

    event_id = event.get("id")
    event_type = event.get("type")
    if not event_id or not event_type:
        raise HTTPException(status_code=400, detail="bad_request")

    connected_account = event.get("account")
    logger.info(
        "stripe_webhook_verified event_id=%s event_type=%s verified_via=%s connect_account_present=%s",
        event_id,
        event_type,
        verified_via,
        bool(connected_account),
    )

    if not record_event_once(db, event_id, event_type):
        return {"ok": True, "duplicate": True}

    obj = (event.get("data") or {}).get("object") or {}
    linked_execution_id: int | None = None

    if event_type in (
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
        "payment_intent.canceled",
        "payment_intent.processing",
        "payment_intent.requires_action",
    ):
        pi_id = obj.get("id")
        status = obj.get("status")
        if pi_id and event_type == "payment_intent.succeeded":
            linked_execution_id = _link_charge_execution(db, pi_id, obj)
        elif pi_id and status:
            linked_execution_id = _update_execution_status(db, pi_id, str(status))

    elif event_type in ("charge.refunded", "refund.updated", "refund.created"):
        refund_id = obj.get("id")
        status = obj.get("status")
        if refund_id and status:
            linked_execution_id = _update_execution_status(db, refund_id, str(status))

    elif event_type == "charge.dispute.created":
        dispute_id = obj.get("id")
        charge_exec = _charge_for_payment_intent(db, obj.get("payment_intent"))
        if charge_exec and dispute_id:
            row = upsert_dispute_execution(
                db,
                charge_exec,
                stripe_dispute_id=dispute_id,
                amount_cents=int(obj.get("amount") or 0),
                currency=str(obj.get("currency") or default_currency()),
                status=str(obj.get("status") or "needs_response"),
            )
            linked_execution_id = row.id

    elif event_type == "charge.dispute.updated":
        dispute_id = obj.get("id")
        status = obj.get("status")
        if dispute_id and status:
            linked_execution_id = _update_execution_status(db, dispute_id, str(status))
            if linked_execution_id is None:
                charge_exec = _charge_for_payment_intent(db, obj.get("payment_intent"))
                if charge_exec:
                    row = upsert_dispute_execution(
                        db,
                        charge_exec,
                        stripe_dispute_id=dispute_id,
                        amount_cents=int(obj.get("amount") or 0),
                        currency=str(obj.get("currency") or default_currency()),
                        status=str(status),
                    )
                    linked_execution_id = row.id

    elif payouts_enabled():
        if event_type in ("transfer.created", "transfer.updated", "transfer.reversed"):
            ingest_transfer(db, obj)

        elif event_type in (
            "payout.created",
            "payout.paid",
            "payout.failed",
            "payout.canceled",
        ):
            if connected_account:
                payout_row = ingest_payout(db, obj, stripe_account_id=str(connected_account))
                if event_type in ("payout.created", "payout.paid"):
                    map_payout_to_transfers_via_balance_transactions(
                        db,
                        payout_row.payout_id,
                        str(connected_account),
                    )

    if linked_execution_id is not None:
        from models.payment_event import PaymentEvent

        event_row = (
            db.query(PaymentEvent)
            .filter(PaymentEvent.external_event_id == event_id)
            .one_or_none()
        )
        if event_row is not None:
            event_row.payment_execution_id = linked_execution_id

    db.commit()
    return {"ok": True}
