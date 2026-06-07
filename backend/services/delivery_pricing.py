"""Deterministic delivery pricing and settlement math."""

from __future__ import annotations

from dataclasses import dataclass

from models.delivery import DeliveryOrder, DeliverySettlementEntry


@dataclass(frozen=True)
class DeliveryPricingPolicy:
    pricing_version: str = "delivery-local-v0-1"
    delivery_base_fee_cents: int = 299
    delivery_per_km_cents: int = 85
    service_fee_bps: int = 1200
    merchant_commission_bps: int = 1500
    tax_bps: int = 900
    small_order_threshold_cents: int = 1200
    small_order_fee_cents: int = 199
    courier_base_payout_cents: int = 350
    courier_per_km_cents: int = 110
    minimum_courier_payout_cents: int = 550
    currency: str = "USD"


@dataclass(frozen=True)
class DeliveryPricingInput:
    items_subtotal_cents: int
    distance_km: float
    tip_cents: int = 0
    merchant_delivery_contribution_cents: int = 0


@dataclass(frozen=True)
class DeliveryPriceBreakdown:
    currency: str
    pricing_version: str
    items_subtotal_cents: int
    delivery_fee_cents: int
    service_fee_cents: int
    small_order_fee_cents: int
    tax_cents: int
    tip_cents: int
    customer_charge_cents: int
    platform_fee_cents: int
    courier_payout_cents: int
    merchant_payout_cents: int


def _non_negative_int(value: int, name: str) -> int:
    amount = int(value)
    if amount < 0:
        raise ValueError(f"{name} must be non-negative")
    return amount


def _money_from_bps(amount_cents: int, bps: int) -> int:
    return int(round((amount_cents * bps) / 10_000))


def quote_delivery_price(
    request: DeliveryPricingInput,
    policy: DeliveryPricingPolicy | None = None,
) -> DeliveryPriceBreakdown:
    policy = policy or DeliveryPricingPolicy()
    subtotal = _non_negative_int(request.items_subtotal_cents, "items_subtotal_cents")
    tip = _non_negative_int(request.tip_cents, "tip_cents")
    merchant_contribution = _non_negative_int(
        request.merchant_delivery_contribution_cents,
        "merchant_delivery_contribution_cents",
    )
    distance_km = max(0.0, float(request.distance_km or 0.0))

    delivery_fee = policy.delivery_base_fee_cents + int(round(distance_km * policy.delivery_per_km_cents))
    service_fee = _money_from_bps(subtotal, policy.service_fee_bps)
    small_order_fee = policy.small_order_fee_cents if 0 < subtotal < policy.small_order_threshold_cents else 0
    tax = _money_from_bps(subtotal + delivery_fee + service_fee + small_order_fee, policy.tax_bps)
    courier_distance_pay = int(round(distance_km * policy.courier_per_km_cents))
    courier_payout = max(policy.minimum_courier_payout_cents, policy.courier_base_payout_cents + courier_distance_pay) + tip
    merchant_commission = _money_from_bps(subtotal, policy.merchant_commission_bps)
    merchant_payout = max(0, subtotal - merchant_commission - merchant_contribution)
    platform_fee = max(0, service_fee + delivery_fee + small_order_fee + merchant_commission - (courier_payout - tip))
    customer_charge = subtotal + delivery_fee + service_fee + small_order_fee + tax + tip

    return DeliveryPriceBreakdown(
        currency=policy.currency,
        pricing_version=policy.pricing_version,
        items_subtotal_cents=subtotal,
        delivery_fee_cents=delivery_fee,
        service_fee_cents=service_fee,
        small_order_fee_cents=small_order_fee,
        tax_cents=tax,
        tip_cents=tip,
        customer_charge_cents=customer_charge,
        platform_fee_cents=platform_fee,
        courier_payout_cents=courier_payout,
        merchant_payout_cents=merchant_payout,
    )


def apply_delivery_price(order: DeliveryOrder, breakdown: DeliveryPriceBreakdown) -> None:
    order.currency = breakdown.currency
    order.pricing_version = breakdown.pricing_version
    order.items_subtotal_cents = breakdown.items_subtotal_cents
    order.delivery_fee_cents = breakdown.delivery_fee_cents
    order.service_fee_cents = breakdown.service_fee_cents
    order.small_order_fee_cents = breakdown.small_order_fee_cents
    order.tax_cents = breakdown.tax_cents
    order.tip_cents = breakdown.tip_cents
    order.customer_charge_cents = breakdown.customer_charge_cents
    order.platform_fee_cents = breakdown.platform_fee_cents
    order.courier_payout_cents = breakdown.courier_payout_cents
    order.merchant_payout_cents = breakdown.merchant_payout_cents


def delivery_refundable_cents(order: DeliveryOrder) -> int:
    return max(0, int(order.customer_charge_cents or 0) - int(order.refunded_cents or 0))


def assert_valid_delivery_refund(order: DeliveryOrder, amount_cents: int) -> None:
    amount = _non_negative_int(amount_cents, "amount_cents")
    if amount <= 0:
        raise ValueError("amount_cents must be greater than zero")
    if amount > delivery_refundable_cents(order):
        raise ValueError("refund_exceeds_customer_charge")


def build_delivery_settlement_entries(order: DeliveryOrder) -> list[DeliverySettlementEntry]:
    evidence = order.evidence_json
    entries = [
        DeliverySettlementEntry(
            order_id=order.id,
            party="customer",
            entry_type="customer_charge",
            amount_cents=order.customer_charge_cents,
            currency=order.currency,
            evidence_json=evidence,
        ),
        DeliverySettlementEntry(
            order_id=order.id,
            party="merchant",
            entry_type="merchant_payout",
            amount_cents=order.merchant_payout_cents,
            currency=order.currency,
            evidence_json=evidence,
        ),
        DeliverySettlementEntry(
            order_id=order.id,
            party="courier",
            entry_type="courier_payout",
            amount_cents=order.courier_payout_cents,
            currency=order.currency,
            evidence_json=evidence,
        ),
        DeliverySettlementEntry(
            order_id=order.id,
            party="platform",
            entry_type="platform_fee",
            amount_cents=order.platform_fee_cents,
            currency=order.currency,
            evidence_json=evidence,
        ),
    ]
    if order.tax_cents > 0:
        entries.append(
            DeliverySettlementEntry(
                order_id=order.id,
                party="tax_authority",
                entry_type="tax_liability",
                amount_cents=order.tax_cents,
                currency=order.currency,
                evidence_json=evidence,
            )
        )
    if order.refunded_cents > 0:
        entries.append(
            DeliverySettlementEntry(
                order_id=order.id,
                party="customer",
                entry_type="refund",
                amount_cents=order.refunded_cents,
                currency=order.currency,
                evidence_json=evidence,
            )
        )
    return entries
