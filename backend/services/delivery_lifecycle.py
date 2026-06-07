"""Delivery order state machine.

The delivery platform has more actors than the ride spine, so the rules live in
their own module instead of overloading ride lifecycle statuses.
"""

from __future__ import annotations

from enum import Enum


class DeliveryLifecycleError(ValueError):
    """Base class for delivery lifecycle failures."""


class InvalidDeliveryTransition(DeliveryLifecycleError):
    """Raised when an order attempts an unsupported status transition."""


class DeliveryOrderStatus(str, Enum):
    CREATED = "created"
    PRICED = "priced"
    PAID = "paid"
    MERCHANT_ACCEPTED = "merchant_accepted"
    PREPARING = "preparing"
    READY_FOR_PICKUP = "ready_for_pickup"
    COURIER_ASSIGNED = "courier_assigned"
    PICKED_UP = "picked_up"
    EN_ROUTE = "en_route"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    FAILED = "failed"


class DeliveryAction(str, Enum):
    PRICE = "price"
    MARK_PAID = "mark_paid"
    MERCHANT_ACCEPT = "merchant_accept"
    START_PREPARING = "start_preparing"
    MARK_READY = "mark_ready"
    ASSIGN_COURIER = "assign_courier"
    PICK_UP = "pick_up"
    START_DELIVERY = "start_delivery"
    DELIVER = "deliver"
    CANCEL = "cancel"
    REFUND = "refund"
    FAIL = "fail"


ACTOR_SYSTEM = "system"
ACTOR_CUSTOMER = "customer"
ACTOR_MERCHANT = "merchant"
ACTOR_COURIER = "courier"
ACTOR_OPS = "ops"
ACTOR_PAYMENT = "payment"
ACTOR_DISPATCH = "dispatch"

TERMINAL_DELIVERY_STATUSES = frozenset(
    {
        DeliveryOrderStatus.DELIVERED,
        DeliveryOrderStatus.CANCELLED,
        DeliveryOrderStatus.REFUNDED,
        DeliveryOrderStatus.FAILED,
    }
)

_TRANSITIONS = {
    (DeliveryOrderStatus.CREATED, DeliveryAction.PRICE, ACTOR_SYSTEM): DeliveryOrderStatus.PRICED,
    (DeliveryOrderStatus.PRICED, DeliveryAction.MARK_PAID, ACTOR_PAYMENT): DeliveryOrderStatus.PAID,
    (DeliveryOrderStatus.PAID, DeliveryAction.MERCHANT_ACCEPT, ACTOR_MERCHANT): DeliveryOrderStatus.MERCHANT_ACCEPTED,
    (
        DeliveryOrderStatus.MERCHANT_ACCEPTED,
        DeliveryAction.START_PREPARING,
        ACTOR_MERCHANT,
    ): DeliveryOrderStatus.PREPARING,
    (DeliveryOrderStatus.PREPARING, DeliveryAction.MARK_READY, ACTOR_MERCHANT): DeliveryOrderStatus.READY_FOR_PICKUP,
    (
        DeliveryOrderStatus.READY_FOR_PICKUP,
        DeliveryAction.ASSIGN_COURIER,
        ACTOR_DISPATCH,
    ): DeliveryOrderStatus.COURIER_ASSIGNED,
    (DeliveryOrderStatus.READY_FOR_PICKUP, DeliveryAction.ASSIGN_COURIER, ACTOR_OPS): DeliveryOrderStatus.COURIER_ASSIGNED,
    (DeliveryOrderStatus.COURIER_ASSIGNED, DeliveryAction.PICK_UP, ACTOR_COURIER): DeliveryOrderStatus.PICKED_UP,
    (DeliveryOrderStatus.PICKED_UP, DeliveryAction.START_DELIVERY, ACTOR_COURIER): DeliveryOrderStatus.EN_ROUTE,
    (DeliveryOrderStatus.EN_ROUTE, DeliveryAction.DELIVER, ACTOR_COURIER): DeliveryOrderStatus.DELIVERED,
}

_CANCELLABLE_STATUSES = frozenset(
    {
        DeliveryOrderStatus.CREATED,
        DeliveryOrderStatus.PRICED,
        DeliveryOrderStatus.PAID,
        DeliveryOrderStatus.MERCHANT_ACCEPTED,
        DeliveryOrderStatus.PREPARING,
        DeliveryOrderStatus.READY_FOR_PICKUP,
        DeliveryOrderStatus.COURIER_ASSIGNED,
    }
)

_FAILABLE_STATUSES = frozenset(status for status in DeliveryOrderStatus if status not in TERMINAL_DELIVERY_STATUSES)
_REFUNDABLE_STATUSES = frozenset({DeliveryOrderStatus.PAID, DeliveryOrderStatus.CANCELLED, DeliveryOrderStatus.DELIVERED})


def normalize_delivery_status(status: DeliveryOrderStatus | str) -> DeliveryOrderStatus:
    try:
        return status if isinstance(status, DeliveryOrderStatus) else DeliveryOrderStatus(status)
    except ValueError as exc:
        raise InvalidDeliveryTransition(f"Unsupported delivery status: {status}") from exc


def normalize_delivery_action(action: DeliveryAction | str) -> DeliveryAction:
    try:
        return action if isinstance(action, DeliveryAction) else DeliveryAction(action)
    except ValueError as exc:
        raise InvalidDeliveryTransition(f"Unsupported delivery action: {action}") from exc


def normalize_delivery_actor(actor: str | Enum) -> str:
    return str(actor.value if isinstance(actor, Enum) else actor)


def to_storage_delivery_status(status: DeliveryOrderStatus | str) -> str:
    return normalize_delivery_status(status).value


def next_delivery_status(
    current_status: DeliveryOrderStatus | str,
    action: DeliveryAction | str,
    actor: str | Enum,
) -> DeliveryOrderStatus:
    current = normalize_delivery_status(current_status)
    requested_action = normalize_delivery_action(action)
    normalized_actor = normalize_delivery_actor(actor)

    if current in TERMINAL_DELIVERY_STATUSES:
        if current == DeliveryOrderStatus.DELIVERED and requested_action == DeliveryAction.REFUND:
            return DeliveryOrderStatus.REFUNDED
        raise InvalidDeliveryTransition(f"Delivery order in terminal status {current.value} cannot change state")

    if requested_action == DeliveryAction.CANCEL and current in _CANCELLABLE_STATUSES:
        if normalized_actor in {ACTOR_CUSTOMER, ACTOR_MERCHANT, ACTOR_OPS}:
            return DeliveryOrderStatus.CANCELLED

    if requested_action == DeliveryAction.FAIL and current in _FAILABLE_STATUSES:
        if normalized_actor in {ACTOR_SYSTEM, ACTOR_PAYMENT, ACTOR_DISPATCH, ACTOR_OPS}:
            return DeliveryOrderStatus.FAILED

    if requested_action == DeliveryAction.REFUND and current in _REFUNDABLE_STATUSES:
        if normalized_actor in {ACTOR_PAYMENT, ACTOR_OPS}:
            return DeliveryOrderStatus.REFUNDED

    next_status = _TRANSITIONS.get((current, requested_action, normalized_actor))
    if next_status is None:
        raise InvalidDeliveryTransition(
            f"{normalized_actor} cannot {requested_action.value} delivery order in status {current.value}"
        )
    return next_status


def assert_valid_delivery_transition(
    current_status: DeliveryOrderStatus | str,
    next_status: DeliveryOrderStatus | str,
    actor: str | Enum,
) -> None:
    expected = normalize_delivery_status(next_status)
    for action in DeliveryAction:
        try:
            if next_delivery_status(current_status, action, actor) == expected:
                return
        except InvalidDeliveryTransition:
            continue
    raise InvalidDeliveryTransition(
        f"{normalize_delivery_actor(actor)} cannot transition delivery order "
        f"from {normalize_delivery_status(current_status).value} to {expected.value}"
    )


def next_actions_for_delivery_status(status: DeliveryOrderStatus | str, actor: str | Enum) -> list[str]:
    current = normalize_delivery_status(status)
    normalized_actor = normalize_delivery_actor(actor)
    actions: list[str] = []
    for action in DeliveryAction:
        try:
            next_delivery_status(current, action, normalized_actor)
        except InvalidDeliveryTransition:
            continue
        actions.append(action.value)
    return actions
