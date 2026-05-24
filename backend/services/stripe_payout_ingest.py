"""Stripe Connect payout ingestion + balance-transaction mapping (HALFAPP_PAYMENTS_EXECUTION_05)."""

from __future__ import annotations

from datetime import datetime, timezone

import stripe
from sqlalchemy.orm import Session

from models.stripe_payout import StripePayout
from models.stripe_payout_transfer import StripePayoutTransfer
from services.stripe_client import stripe_init


def _stripe_ts_to_naive(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(tzinfo=None)


def ingest_payout(db: Session, payout_obj: dict, *, stripe_account_id: str) -> StripePayout:
    payout_id = str(payout_obj.get("id") or "")
    if not payout_id:
        raise ValueError("payout_id_missing")

    row = db.query(StripePayout).filter(StripePayout.payout_id == payout_id).one_or_none()
    if row is None:
        row = StripePayout(payout_id=payout_id, stripe_account_id=stripe_account_id)

    row.stripe_account_id = stripe_account_id
    row.amount_cents = int(payout_obj.get("amount") or 0)
    row.currency = str(payout_obj.get("currency") or "usd").lower()
    row.status = str(payout_obj.get("status") or "unknown")
    row.created_at = _stripe_ts_to_naive(payout_obj.get("created"))
    row.arrival_date = _stripe_ts_to_naive(payout_obj.get("arrival_date"))

    db.add(row)
    db.flush()
    return row


def map_payout_to_transfers_via_balance_transactions(
    db: Session,
    payout_id: str,
    stripe_account_id: str,
) -> int:
    """
    List balance transactions for a payout on the connected account and record transfer ids.
    """
    stripe_init()
    txns = stripe.BalanceTransaction.list(
        payout=payout_id,
        limit=100,
        stripe_account=stripe_account_id,
    )

    linked = 0
    for txn in txns.get("data", []):
        src = txn.get("source")
        typ = txn.get("type")
        if typ == "transfer" and isinstance(src, str) and src.startswith("tr_"):
            existing = (
                db.query(StripePayoutTransfer)
                .filter(
                    StripePayoutTransfer.payout_id == payout_id,
                    StripePayoutTransfer.transfer_id == src,
                )
                .one_or_none()
            )
            if existing is None:
                db.add(
                    StripePayoutTransfer(
                        payout_id=payout_id,
                        transfer_id=src,
                        stripe_account_id=stripe_account_id,
                    )
                )
                linked += 1

    db.flush()
    return linked
