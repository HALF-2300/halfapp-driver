"""Stripe transfer webhook ingestion (HALFAPP_PAYMENTS_EXECUTION_05)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.payment_execution import PaymentExecution
from models.stripe_transfer import StripeTransfer


def _stripe_ts_to_naive(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(tzinfo=None)


def ingest_transfer(db: Session, transfer_obj: dict) -> StripeTransfer:
    transfer_id = str(transfer_obj.get("id") or "")
    if not transfer_id:
        raise ValueError("transfer_id_missing")

    row = db.query(StripeTransfer).filter(StripeTransfer.transfer_id == transfer_id).one_or_none()
    if row is None:
        row = StripeTransfer(transfer_id=transfer_id)

    row.amount_cents = int(transfer_obj.get("amount") or 0)
    row.currency = str(transfer_obj.get("currency") or "usd").lower()
    row.destination_account_id = transfer_obj.get("destination")
    row.source_transaction = transfer_obj.get("source_transaction")
    row.reversed = bool(transfer_obj.get("reversed", False))
    row.created_at = _stripe_ts_to_naive(transfer_obj.get("created"))

    source = row.source_transaction
    if source and str(source).startswith("ch_"):
        execution = (
            db.query(PaymentExecution)
            .filter(PaymentExecution.external_charge_id == str(source))
            .one_or_none()
        )
        if execution is not None:
            row.payment_execution_id = execution.id

    db.add(row)
    db.flush()
    return row
