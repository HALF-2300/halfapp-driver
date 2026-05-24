"""Webhook event deduplication (HALFAPP_PAYMENTS_EXECUTION_02_5)."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.payment_event import PaymentEvent


def record_event_once(
    db: Session,
    external_event_id: str,
    event_type: str,
    payment_execution_id: int | None = None,
) -> bool:
    """
    Record Stripe evt_* id once per delivery attempt chain.
    Returns True if this is the first time (caller should process), False if duplicate.
    Uses flush only — caller commits the surrounding transaction.
    """
    existing = (
        db.query(PaymentEvent)
        .filter(PaymentEvent.external_event_id == external_event_id)
        .one_or_none()
    )
    if existing is not None:
        return False

    row = PaymentEvent(
        external_event_id=external_event_id,
        event_type=event_type,
        payment_execution_id=payment_execution_id,
    )
    db.add(row)
    try:
        db.flush()
        return True
    except IntegrityError:
        db.rollback()
        return False
