from enum import Enum


class LifecycleError(ValueError):
    """Base class for domain lifecycle failures."""


class InvalidRideTransition(LifecycleError):
    """Raised when a requested ride status transition is not allowed."""


class DriverUnavailableForRide(LifecycleError):
    """Raised when a driver's state does not permit accepting a ride."""


class DriverStatus(str, Enum):
    OFFLINE = "offline"
    AVAILABLE = "available"
    BUSY = "busy"
    SUSPENDED = "suspended"


class RideStatus(str, Enum):
    REQUESTED = "requested"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    DRIVER_ARRIVED = "driver_arrived"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


_TERMINAL_RIDE_STATUSES = frozenset({RideStatus.COMPLETED, RideStatus.CANCELLED})


class RideAction(str, Enum):
    ACCEPT = "accept"
    ARRIVE = "arrive"
    START = "start"
    COMPLETE = "complete"
    CANCEL = "cancel"


class NotificationType(str, Enum):
    RIDE_REQUESTED = "ride_requested"
    RIDE_ACCEPTED = "ride_accepted"
    RIDE_CANCELLED = "ride_cancelled"
    RIDE_COMPLETED = "ride_completed"
    SYSTEM = "system"


_ACTOR_DRIVER = "driver"
_ACTOR_RIDER = "customer"

_TRANSITIONS = {
    (RideStatus.REQUESTED, RideAction.ACCEPT, _ACTOR_DRIVER): RideStatus.ACCEPTED,
    (RideStatus.ACCEPTED, RideAction.ARRIVE, _ACTOR_DRIVER): RideStatus.DRIVER_ARRIVED,
    (RideStatus.DRIVER_ARRIVED, RideAction.START, _ACTOR_DRIVER): RideStatus.IN_PROGRESS,
    (RideStatus.IN_PROGRESS, RideAction.COMPLETE, _ACTOR_DRIVER): RideStatus.COMPLETED,
    (RideStatus.REQUESTED, RideAction.CANCEL, _ACTOR_RIDER): RideStatus.CANCELLED,
    (RideStatus.ACCEPTED, RideAction.CANCEL, _ACTOR_RIDER): RideStatus.CANCELLED,
    (RideStatus.DRIVER_ARRIVED, RideAction.CANCEL, _ACTOR_RIDER): RideStatus.CANCELLED,
    (RideStatus.IN_PROGRESS, RideAction.CANCEL, _ACTOR_RIDER): RideStatus.CANCELLED,
}


def normalize_driver_status(status: DriverStatus | str) -> DriverStatus:
    try:
        return status if isinstance(status, DriverStatus) else DriverStatus(status)
    except ValueError as exc:
        raise DriverUnavailableForRide(f"Unsupported driver status: {status}") from exc


def normalize_ride_status(status: RideStatus | str) -> RideStatus:
    try:
        return status if isinstance(status, RideStatus) else RideStatus(status)
    except ValueError as exc:
        raise InvalidRideTransition(f"Unsupported ride status: {status}") from exc


def normalize_ride_action(action: RideAction | str) -> RideAction:
    try:
        return action if isinstance(action, RideAction) else RideAction(action)
    except ValueError as exc:
        raise InvalidRideTransition(f"Unsupported ride action: {action}") from exc


def normalize_actor_role(actor_role: str | Enum) -> str:
    value = actor_role.value if isinstance(actor_role, Enum) else actor_role
    return "customer" if value == "rider" else str(value)


def to_storage_ride_status(status: RideStatus | str) -> str:
    return normalize_ride_status(status).value


def can_driver_accept_ride(driver_status: DriverStatus | str, ride_status: RideStatus | str) -> bool:
    try:
        return (
            normalize_driver_status(driver_status) == DriverStatus.AVAILABLE
            and normalize_ride_status(ride_status) == RideStatus.REQUESTED
        )
    except LifecycleError:
        return False


def assert_driver_can_accept_ride(driver_status: DriverStatus | str, ride_status: RideStatus | str) -> None:
    normalized_driver_status = normalize_driver_status(driver_status)
    normalized_ride_status = normalize_ride_status(ride_status)
    if normalized_driver_status != DriverStatus.AVAILABLE:
        raise DriverUnavailableForRide(
            f"Driver must be available to accept a ride; current status is {normalized_driver_status.value}"
        )
    if normalized_ride_status != RideStatus.REQUESTED:
        raise InvalidRideTransition(
            f"Driver can accept only requested rides; current status is {normalized_ride_status.value}"
        )


def _assert_not_terminal(current: RideStatus) -> None:
    if current in _TERMINAL_RIDE_STATUSES:
        raise InvalidRideTransition(f"Ride in terminal status {current.value} cannot change state")


def next_ride_status(
    current_status: RideStatus | str,
    action: RideAction | str,
    actor_role: str | Enum,
) -> RideStatus:
    current = normalize_ride_status(current_status)
    _assert_not_terminal(current)
    normalized_action = normalize_ride_action(action)
    role = normalize_actor_role(actor_role)
    next_status = _TRANSITIONS.get((current, normalized_action, role))
    if next_status is None:
        raise InvalidRideTransition(f"{role} cannot {normalized_action.value} ride in status {current.value}")
    return next_status


def assert_valid_ride_transition(
    current_status: RideStatus | str,
    next_status: RideStatus | str,
    actor_role: str | Enum,
) -> None:
    current = normalize_ride_status(current_status)
    _assert_not_terminal(current)
    expected_next = normalize_ride_status(next_status)
    role = normalize_actor_role(actor_role)
    if (current, expected_next, role) not in {
        (from_status, to_status, transition_role)
        for (from_status, _, transition_role), to_status in _TRANSITIONS.items()
    }:
        raise InvalidRideTransition(
            f"{role} cannot transition ride from {current.value} to {expected_next.value}"
        )


def release_accepted_ride_to_pool(current_status: RideStatus | str, actor_role: str | Enum) -> RideStatus:
    current = normalize_ride_status(current_status)
    role = normalize_actor_role(actor_role)
    if current != RideStatus.ACCEPTED or role != _ACTOR_DRIVER:
        raise InvalidRideTransition(f"{role} cannot release ride in status {current.value}")
    return RideStatus.REQUESTED


def next_actions_for(status: RideStatus | str) -> list[str]:
    """Driver-visible lifecycle actions for cockpit session recovery."""
    current = normalize_ride_status(status)
    if current == RideStatus.ACCEPTED:
        return [RideAction.ARRIVE.value]
    if current == RideStatus.DRIVER_ARRIVED:
        return [RideAction.START.value]
    if current == RideStatus.IN_PROGRESS:
        return [RideAction.COMPLETE.value]
    return []
