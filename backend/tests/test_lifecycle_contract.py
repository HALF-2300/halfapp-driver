import pytest

from models.user import UserRole
from schemas.drivers import DriverStatusResponse
from schemas.notifications import NotificationResponse
from schemas.rides import RideActionRequest, RideCreateRequest, RideResponse
from services.lifecycle import (
    DriverStatus,
    DriverUnavailableForRide,
    InvalidRideTransition,
    NotificationType,
    RideAction,
    RideStatus,
    assert_driver_can_accept_ride,
    assert_valid_ride_transition,
    can_driver_accept_ride,
    next_ride_status,
    normalize_ride_status,
)


def test_lifecycle_contract_is_pure_and_defines_canonical_values():
    assert [status.value for status in DriverStatus] == [
        "offline",
        "available",
        "busy",
        "suspended",
    ]
    assert [status.value for status in RideStatus] == [
        "requested",
        "offered",
        "accepted",
        "driver_arrived",
        "in_progress",
        "completed",
        "cancelled",
    ]
    assert [action.value for action in RideAction] == ["accept", "arrive", "start", "complete", "cancel"]
    assert [kind.value for kind in NotificationType] == [
        "ride_requested",
        "ride_accepted",
        "ride_cancelled",
        "ride_completed",
        "system",
    ]


def test_driver_accept_contract():
    assert can_driver_accept_ride(DriverStatus.AVAILABLE, RideStatus.REQUESTED)
    assert not can_driver_accept_ride(DriverStatus.OFFLINE, RideStatus.REQUESTED)
    assert not can_driver_accept_ride(DriverStatus.AVAILABLE, RideStatus.COMPLETED)

    assert_driver_can_accept_ride(DriverStatus.AVAILABLE, RideStatus.REQUESTED)
    with pytest.raises(DriverUnavailableForRide):
        assert_driver_can_accept_ride(DriverStatus.OFFLINE, RideStatus.REQUESTED)
    with pytest.raises(InvalidRideTransition):
        assert_driver_can_accept_ride(DriverStatus.AVAILABLE, RideStatus.COMPLETED)


def test_ride_state_machine_contract():
    assert next_ride_status(RideStatus.REQUESTED, RideAction.ACCEPT, UserRole.DRIVER) == RideStatus.ACCEPTED
    assert next_ride_status(RideStatus.ACCEPTED, RideAction.ARRIVE, UserRole.DRIVER) == RideStatus.DRIVER_ARRIVED
    assert next_ride_status(RideStatus.DRIVER_ARRIVED, RideAction.START, UserRole.DRIVER) == RideStatus.IN_PROGRESS
    assert next_ride_status(RideStatus.IN_PROGRESS, RideAction.COMPLETE, UserRole.DRIVER) == RideStatus.COMPLETED
    assert next_ride_status(RideStatus.IN_PROGRESS, RideAction.CANCEL, UserRole.CUSTOMER) == RideStatus.CANCELLED

    assert_valid_ride_transition(RideStatus.REQUESTED, RideStatus.ACCEPTED, UserRole.DRIVER)
    with pytest.raises(InvalidRideTransition):
        next_ride_status(RideStatus.COMPLETED, RideAction.CANCEL, UserRole.CUSTOMER)
    with pytest.raises(InvalidRideTransition):
        next_ride_status(RideStatus.COMPLETED, RideAction.ACCEPT, UserRole.DRIVER)


def test_invalid_ride_status_string_raises_invalid_transition():
    with pytest.raises(InvalidRideTransition, match="Unsupported ride status"):
        normalize_ride_status("not_a_real_status")


def test_public_schemas_reference_canonical_enums():
    assert RideCreateRequest.model_fields["pickup_location"].is_required()
    assert RideCreateRequest.model_fields["dropoff_location"].is_required()
    assert RideActionRequest.model_fields["action"].annotation is RideAction
    assert RideResponse.model_fields["status"].annotation is RideStatus
    assert DriverStatusResponse.model_fields["status"].annotation is DriverStatus
    assert NotificationResponse.model_fields["type"].annotation is NotificationType
