"""Delivery order orchestration.

Routes call these helpers instead of mutating DeliveryOrder.status directly.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any

from sqlalchemy.orm import Session

from models.delivery import DeliveryOrder, DeliverySettlementEntry
from services.datetime_utils import utc_now_naive
from services.delivery_lifecycle import (
    ACTOR_COURIER,
    ACTOR_DISPATCH,
    ACTOR_MERCHANT,
    ACTOR_OPS,
    ACTOR_PAYMENT,
    ACTOR_SYSTEM,
    DeliveryAction,
    DeliveryOrderStatus,
    InvalidDeliveryTransition,
    next_delivery_status,
    to_storage_delivery_status,
)
from services.delivery_pricing import (
    DeliveryPricingInput,
    apply_delivery_price,
    assert_valid_delivery_refund,
    build_delivery_settlement_entries,
    delivery_refundable_cents,
    quote_delivery_price,
)


class DeliveryOrderAccessError(PermissionError):
    pass


class DeliveryOrderNotFound(LookupError):
    pass


_STATUS_TIMESTAMP_FIELDS = {
    DeliveryOrderStatus.PRICED: "priced_at",
    DeliveryOrderStatus.PAID: "paid_at",
    DeliveryOrderStatus.MERCHANT_ACCEPTED: "merchant_accepted_at",
    DeliveryOrderStatus.PREPARING: "preparing_at",
    DeliveryOrderStatus.READY_FOR_PICKUP: "ready_for_pickup_at",
    DeliveryOrderStatus.COURIER_ASSIGNED: "courier_assigned_at",
    DeliveryOrderStatus.PICKED_UP: "picked_up_at",
    DeliveryOrderStatus.EN_ROUTE: "en_route_at",
    DeliveryOrderStatus.DELIVERED: "delivered_at",
    DeliveryOrderStatus.CANCELLED: "cancelled_at",
    DeliveryOrderStatus.REFUNDED: "refunded_at",
    DeliveryOrderStatus.FAILED: "failed_at",
}


def _merchant_code(merchant_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", merchant_name.lower()).strip("-")
    return f"local-{slug or 'merchant'}"


def transition_delivery_order(
    order: DeliveryOrder,
    *,
    action: DeliveryAction | str,
    actor: str,
    reason: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> DeliveryOrder:
    from_status = DeliveryOrderStatus(order.status)
    to_status = next_delivery_status(from_status, action, actor)
    now = utc_now_naive()
    order.status = to_storage_delivery_status(to_status)
    order.updated_at = now
    timestamp_field = _STATUS_TIMESTAMP_FIELDS.get(to_status)
    if timestamp_field and getattr(order, timestamp_field) is None:
        setattr(order, timestamp_field, now)
    if to_status == DeliveryOrderStatus.CANCELLED:
        order.cancellation_reason = reason
    if to_status == DeliveryOrderStatus.FAILED:
        order.failure_reason = reason
    if evidence:
        order.evidence_json = json.dumps(
            {
                "transition": {
                    "from": from_status.value,
                    "to": to_status.value,
                    "actor": actor,
                    "action": str(action.value if isinstance(action, DeliveryAction) else action),
                    "at": now.isoformat() + "Z",
                },
                **evidence,
            },
            sort_keys=True,
        )
    return order


def create_paid_delivery_order(
    db: Session,
    *,
    customer_id: int,
    merchant_name: str,
    pickup_address: str,
    dropoff_address: str,
    items_subtotal_cents: int,
    distance_km: float,
    tip_cents: int = 0,
    items_summary: str | None = None,
    delivery_notes: str | None = None,
    contactless: bool = True,
    payment_provider: str = "local_test_hold",
    payment_reference: str | None = None,
) -> DeliveryOrder:
    merchant = merchant_name.strip()
    if not merchant:
        raise ValueError("merchant_name is required")
    if not pickup_address.strip() or not dropoff_address.strip():
        raise ValueError("pickup_address and dropoff_address are required")

    order = DeliveryOrder(
        customer_id=customer_id,
        merchant_name=merchant,
        merchant_access_code=_merchant_code(merchant),
        pickup_address=pickup_address.strip(),
        dropoff_address=dropoff_address.strip(),
        items_summary=(items_summary or "").strip() or None,
        delivery_notes=(delivery_notes or "").strip() or None,
        distance_km=max(0.0, float(distance_km or 0.0)),
        contactless=1 if contactless else 0,
        status=DeliveryOrderStatus.CREATED.value,
        payment_provider=payment_provider,
        payment_reference=payment_reference,
    )
    breakdown = quote_delivery_price(
        DeliveryPricingInput(
            items_subtotal_cents=items_subtotal_cents,
            distance_km=order.distance_km,
            tip_cents=tip_cents,
        )
    )
    apply_delivery_price(order, breakdown)
    db.add(order)
    db.flush()
    transition_delivery_order(order, action=DeliveryAction.PRICE, actor=ACTOR_SYSTEM)
    transition_delivery_order(order, action=DeliveryAction.MARK_PAID, actor=ACTOR_PAYMENT)
    if not order.payment_reference:
        order.payment_reference = f"local-test-hold-{order.id}"
    db.flush()
    return order


def get_delivery_order_or_404(db: Session, order_id: int) -> DeliveryOrder:
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if order is None:
        raise DeliveryOrderNotFound("Delivery order not found")
    return order


def merchant_can_access(order: DeliveryOrder, merchant_access_code: str | None) -> bool:
    return bool(merchant_access_code) and merchant_access_code == order.merchant_access_code


def merchant_accept_order(order: DeliveryOrder) -> DeliveryOrder:
    return transition_delivery_order(order, action=DeliveryAction.MERCHANT_ACCEPT, actor=ACTOR_MERCHANT)


def merchant_start_preparing(order: DeliveryOrder) -> DeliveryOrder:
    return transition_delivery_order(order, action=DeliveryAction.START_PREPARING, actor=ACTOR_MERCHANT)


def merchant_mark_ready(order: DeliveryOrder) -> DeliveryOrder:
    return transition_delivery_order(order, action=DeliveryAction.MARK_READY, actor=ACTOR_MERCHANT)


def merchant_reject_order(order: DeliveryOrder, reason: str | None = None) -> DeliveryOrder:
    return transition_delivery_order(order, action=DeliveryAction.CANCEL, actor=ACTOR_MERCHANT, reason=reason)


def assign_courier(order: DeliveryOrder, courier_id: int, *, actor: str = ACTOR_DISPATCH) -> DeliveryOrder:
    transitioned = transition_delivery_order(order, action=DeliveryAction.ASSIGN_COURIER, actor=actor)
    transitioned.courier_id = courier_id
    return transitioned


def courier_pickup_order(order: DeliveryOrder, courier_id: int) -> DeliveryOrder:
    _assert_courier_owns_order(order, courier_id)
    return transition_delivery_order(order, action=DeliveryAction.PICK_UP, actor=ACTOR_COURIER)


def courier_start_delivery(order: DeliveryOrder, courier_id: int) -> DeliveryOrder:
    _assert_courier_owns_order(order, courier_id)
    return transition_delivery_order(order, action=DeliveryAction.START_DELIVERY, actor=ACTOR_COURIER)


def courier_deliver_order(order: DeliveryOrder, courier_id: int, *, proof: dict[str, Any] | None = None) -> DeliveryOrder:
    _assert_courier_owns_order(order, courier_id)
    return transition_delivery_order(order, action=DeliveryAction.DELIVER, actor=ACTOR_COURIER, evidence=proof)


def cancel_delivery_order(order: DeliveryOrder, *, actor: str, reason: str | None = None) -> DeliveryOrder:
    return transition_delivery_order(order, action=DeliveryAction.CANCEL, actor=actor, reason=reason)


def refund_delivery_order(order: DeliveryOrder, *, amount_cents: int, reason: str | None = None) -> DeliveryOrder:
    assert_valid_delivery_refund(order, amount_cents)
    order.refunded_cents = int(order.refunded_cents or 0) + int(amount_cents)
    evidence = {"refund": {"amount_cents": int(amount_cents), "reason": reason or "ops_refund"}}
    return transition_delivery_order(order, action=DeliveryAction.REFUND, actor=ACTOR_OPS, reason=reason, evidence=evidence)


def refund_eligibility(order: DeliveryOrder) -> dict[str, Any]:
    refundable = delivery_refundable_cents(order)
    return {
        "eligible": refundable > 0 and order.status in {"paid", "cancelled", "delivered"},
        "refundable_cents": refundable,
        "customer_charge_cents": order.customer_charge_cents,
        "already_refunded_cents": order.refunded_cents,
        "reason": "eligible_for_recorded_refund" if refundable > 0 else "nothing_refundable",
    }


def ensure_delivery_settlement_entries(db: Session, order: DeliveryOrder) -> list[DeliverySettlementEntry]:
    existing = (
        db.query(DeliverySettlementEntry)
        .filter(DeliverySettlementEntry.order_id == order.id)
        .order_by(DeliverySettlementEntry.id.asc())
        .all()
    )
    if existing:
        has_refund = any(entry.entry_type == "refund" for entry in existing)
        if int(order.refunded_cents or 0) > 0 and not has_refund:
            refund_entries = [entry for entry in build_delivery_settlement_entries(order) if entry.entry_type == "refund"]
            for entry in refund_entries:
                db.add(entry)
                existing.append(entry)
            db.flush()
        return existing
    entries = build_delivery_settlement_entries(order)
    for entry in entries:
        db.add(entry)
    db.flush()
    return entries


def delivery_order_to_dict(order: DeliveryOrder, *, include_sensitive: bool = False) -> dict[str, Any]:
    payload = {
        "id": order.id,
        "customer_id": order.customer_id,
        "courier_id": order.courier_id,
        "merchant_name": order.merchant_name,
        "status": order.status,
        "pickup_address": order.pickup_address,
        "dropoff_address": order.dropoff_address,
        "items_summary": order.items_summary,
        "delivery_notes": order.delivery_notes,
        "distance_km": order.distance_km,
        "contactless": bool(order.contactless),
        "currency": order.currency,
        "pricing": {
            "items_subtotal_cents": order.items_subtotal_cents,
            "delivery_fee_cents": order.delivery_fee_cents,
            "service_fee_cents": order.service_fee_cents,
            "small_order_fee_cents": order.small_order_fee_cents,
            "tax_cents": order.tax_cents,
            "tip_cents": order.tip_cents,
            "customer_charge_cents": order.customer_charge_cents,
            "platform_fee_cents": order.platform_fee_cents,
            "courier_payout_cents": order.courier_payout_cents,
            "merchant_payout_cents": order.merchant_payout_cents,
            "refunded_cents": order.refunded_cents,
            "pricing_version": order.pricing_version,
        },
        "payment": {
            "provider": order.payment_provider,
            "reference": order.payment_reference,
            "production_ready": False,
            "truth_label": "local test hold; replace with PSP charge before launch",
        },
        "refund": refund_eligibility(order),
        "evidence": json.loads(order.evidence_json) if order.evidence_json else None,
        "created_at": _iso(order.created_at),
        "priced_at": _iso(order.priced_at),
        "paid_at": _iso(order.paid_at),
        "merchant_accepted_at": _iso(order.merchant_accepted_at),
        "preparing_at": _iso(order.preparing_at),
        "ready_for_pickup_at": _iso(order.ready_for_pickup_at),
        "courier_assigned_at": _iso(order.courier_assigned_at),
        "picked_up_at": _iso(order.picked_up_at),
        "en_route_at": _iso(order.en_route_at),
        "delivered_at": _iso(order.delivered_at),
        "cancelled_at": _iso(order.cancelled_at),
        "refunded_at": _iso(order.refunded_at),
        "failed_at": _iso(order.failed_at),
        "updated_at": _iso(order.updated_at),
        "cancellation_reason": order.cancellation_reason,
        "failure_reason": order.failure_reason,
    }
    if include_sensitive:
        payload["merchant_access_code"] = order.merchant_access_code
    return payload


def settlement_entries_to_dict(entries: list[DeliverySettlementEntry]) -> list[dict[str, Any]]:
    return [
        {
            "id": entry.id,
            "order_id": entry.order_id,
            "party": entry.party,
            "entry_type": entry.entry_type,
            "amount_cents": entry.amount_cents,
            "currency": entry.currency,
            "status": entry.status,
            "evidence": json.loads(entry.evidence_json) if entry.evidence_json else None,
            "created_at": _iso(entry.created_at),
        }
        for entry in entries
    ]


def price_breakdown_to_dict(input_payload: DeliveryPricingInput) -> dict[str, Any]:
    return asdict(quote_delivery_price(input_payload))


def _assert_courier_owns_order(order: DeliveryOrder, courier_id: int) -> None:
    if order.courier_id != courier_id:
        raise DeliveryOrderAccessError("Delivery order is not assigned to this courier")


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() + "Z" if value.tzinfo is None else value.isoformat()
