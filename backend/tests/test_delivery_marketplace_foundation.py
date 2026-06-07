import pytest

from models.delivery import DeliveryOrder
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
    next_actions_for_delivery_status,
    next_delivery_status,
)
from services.delivery_pricing import (
    DeliveryPricingInput,
    DeliveryPricingPolicy,
    apply_delivery_price,
    assert_valid_delivery_refund,
    build_delivery_settlement_entries,
    delivery_refundable_cents,
    quote_delivery_price,
)


def test_delivery_order_lifecycle_happy_path_is_strict():
    status = DeliveryOrderStatus.CREATED
    status = next_delivery_status(status, DeliveryAction.PRICE, ACTOR_SYSTEM)
    assert status == DeliveryOrderStatus.PRICED
    status = next_delivery_status(status, DeliveryAction.MARK_PAID, ACTOR_PAYMENT)
    assert status == DeliveryOrderStatus.PAID
    status = next_delivery_status(status, DeliveryAction.MERCHANT_ACCEPT, ACTOR_MERCHANT)
    assert status == DeliveryOrderStatus.MERCHANT_ACCEPTED
    status = next_delivery_status(status, DeliveryAction.START_PREPARING, ACTOR_MERCHANT)
    assert status == DeliveryOrderStatus.PREPARING
    status = next_delivery_status(status, DeliveryAction.MARK_READY, ACTOR_MERCHANT)
    assert status == DeliveryOrderStatus.READY_FOR_PICKUP
    status = next_delivery_status(status, DeliveryAction.ASSIGN_COURIER, ACTOR_DISPATCH)
    assert status == DeliveryOrderStatus.COURIER_ASSIGNED
    status = next_delivery_status(status, DeliveryAction.PICK_UP, ACTOR_COURIER)
    assert status == DeliveryOrderStatus.PICKED_UP
    status = next_delivery_status(status, DeliveryAction.START_DELIVERY, ACTOR_COURIER)
    assert status == DeliveryOrderStatus.EN_ROUTE
    status = next_delivery_status(status, DeliveryAction.DELIVER, ACTOR_COURIER)
    assert status == DeliveryOrderStatus.DELIVERED


def test_delivery_order_rejects_random_state_jumps():
    with pytest.raises(InvalidDeliveryTransition):
        next_delivery_status(DeliveryOrderStatus.CREATED, DeliveryAction.DELIVER, ACTOR_COURIER)

    with pytest.raises(InvalidDeliveryTransition):
        next_delivery_status(DeliveryOrderStatus.PAID, DeliveryAction.PICK_UP, ACTOR_COURIER)

    with pytest.raises(InvalidDeliveryTransition):
        next_delivery_status(DeliveryOrderStatus.DELIVERED, DeliveryAction.CANCEL, ACTOR_OPS)


def test_delivery_order_failure_cancellation_and_refund_boundaries():
    assert (
        next_delivery_status(DeliveryOrderStatus.PREPARING, DeliveryAction.CANCEL, ACTOR_MERCHANT)
        == DeliveryOrderStatus.CANCELLED
    )
    assert (
        next_delivery_status(DeliveryOrderStatus.COURIER_ASSIGNED, DeliveryAction.FAIL, ACTOR_OPS)
        == DeliveryOrderStatus.FAILED
    )
    assert (
        next_delivery_status(DeliveryOrderStatus.DELIVERED, DeliveryAction.REFUND, ACTOR_PAYMENT)
        == DeliveryOrderStatus.REFUNDED
    )
    dispatch_actions = next_actions_for_delivery_status(DeliveryOrderStatus.READY_FOR_PICKUP, ACTOR_DISPATCH)
    assert DeliveryAction.ASSIGN_COURIER.value in dispatch_actions
    assert DeliveryAction.FAIL.value in dispatch_actions


def test_delivery_pricing_keeps_customer_merchant_courier_and_platform_math_visible():
    breakdown = quote_delivery_price(
        DeliveryPricingInput(items_subtotal_cents=2400, distance_km=3.2, tip_cents=500),
        DeliveryPricingPolicy(
            delivery_base_fee_cents=300,
            delivery_per_km_cents=100,
            service_fee_bps=1000,
            merchant_commission_bps=1500,
            tax_bps=1000,
            courier_base_payout_cents=350,
            courier_per_km_cents=100,
            minimum_courier_payout_cents=600,
        ),
    )

    assert breakdown.delivery_fee_cents == 620
    assert breakdown.service_fee_cents == 240
    assert breakdown.tax_cents == 326
    assert breakdown.tip_cents == 500
    assert breakdown.customer_charge_cents == 4086
    assert breakdown.courier_payout_cents == 1170
    assert breakdown.merchant_payout_cents == 2040
    assert breakdown.platform_fee_cents == 550


def test_delivery_settlement_entries_and_refund_guard_use_order_amounts():
    order = DeliveryOrder(
        merchant_name="Pearl Market",
        pickup_address="10 Market St",
        dropoff_address="88 Local Ave",
        distance_km=2.5,
        evidence_json='{"dropoff_photo":"stored-object-ref"}',
    )
    breakdown = quote_delivery_price(DeliveryPricingInput(items_subtotal_cents=1800, distance_km=2.5, tip_cents=300))
    apply_delivery_price(order, breakdown)
    order.id = 42
    order.refunded_cents = 500

    assert delivery_refundable_cents(order) == breakdown.customer_charge_cents - 500
    assert_valid_delivery_refund(order, 100)
    with pytest.raises(ValueError):
        assert_valid_delivery_refund(order, breakdown.customer_charge_cents)

    entries = build_delivery_settlement_entries(order)
    by_type = {entry.entry_type: entry for entry in entries}
    assert by_type["customer_charge"].amount_cents == breakdown.customer_charge_cents
    assert by_type["merchant_payout"].amount_cents == breakdown.merchant_payout_cents
    assert by_type["courier_payout"].amount_cents == breakdown.courier_payout_cents
    assert by_type["platform_fee"].amount_cents == breakdown.platform_fee_cents
    assert by_type["tax_liability"].amount_cents == breakdown.tax_cents
    assert by_type["refund"].amount_cents == 500
