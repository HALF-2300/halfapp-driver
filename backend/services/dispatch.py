from abc import ABC, abstractmethod

from typing import List

from sqlalchemy import update
from sqlalchemy.orm import Session

from models.metrics import RideVisibility
from models.ride import Ride
from services.lifecycle import DriverStatus, RideStatus, can_driver_accept_ride, to_storage_ride_status
from services.datetime_utils import utc_now_naive
from services.metrics import DISPATCH_POLICY_VERSION, active_hidden_filter, rank_available_rides


class DispatchError(Exception):
    """Base class for transparent dispatch failures."""


class RideNotFound(DispatchError):
    pass


class RideAlreadyClaimed(DispatchError):
    pass


class RideNotAvailable(DispatchError):
    pass


class BaseDispatchPolicy(ABC):
    """Policy boundary for dispatch and ride-claim decisions."""

    @abstractmethod
    def get_available_rides(self, db: Session, driver_id: int, **kwargs) -> List[Ride]:
        raise NotImplementedError

    @abstractmethod
    def claim_ride(self, db: Session, ride_id: int, driver_id: int) -> Ride:
        raise NotImplementedError


class OpenBoardDispatchPolicy(BaseDispatchPolicy):
    """Open board: every eligible driver sees the pool, first atomic claim wins."""

    policy_id = DISPATCH_POLICY_VERSION
    policy_name = "Open Board v1"

    def get_available_rides(self, db: Session, driver_id: int, **kwargs) -> List[Ride]:
        driver = kwargs.get("driver")
        rides = (
            db.query(Ride)
            .outerjoin(
                RideVisibility,
                (RideVisibility.ride_id == Ride.id)
                & (RideVisibility.driver_id == driver_id)
                & active_hidden_filter(),
            )
            .filter(Ride.status == to_storage_ride_status(RideStatus.REQUESTED), Ride.driver_id.is_(None))
            .filter(RideVisibility.id.is_(None))
            .order_by(Ride.created_at.asc(), Ride.id.asc())
            .all()
        )
        if driver is not None:
            return rank_available_rides(db, driver=driver, rides=rides)
        return rides

    def claim_ride(self, db: Session, ride_id: int, driver_id: int) -> Ride:
        """Claim under SELECT ... FOR UPDATE, then atomic conditional UPDATE.

        Row lock serializes competing claims in one DB transaction (PostgreSQL).
        The conditional UPDATE ensures exactly one winner across connections
        (including SQLite test workers with separate sessions).
        """
        ride = (
            db.query(Ride)
            .filter(Ride.id == ride_id)
            .with_for_update()
            .first()
        )
        if not ride:
            raise RideNotFound
        if ride.driver_id is not None:
            raise RideAlreadyClaimed
        if ride.status != to_storage_ride_status(RideStatus.REQUESTED):
            raise RideNotAvailable
        if not can_driver_accept_ride(DriverStatus.AVAILABLE, ride.status):
            raise RideNotAvailable

        accepted_at = utc_now_naive()
        result = db.execute(
            update(Ride)
            .where(
                Ride.id == ride_id,
                Ride.driver_id.is_(None),
                Ride.status == to_storage_ride_status(RideStatus.REQUESTED),
            )
            .values(
                driver_id=driver_id,
                status=to_storage_ride_status(RideStatus.ACCEPTED),
                accepted_at=accepted_at,
            )
        )
        if result.rowcount == 1:
            db.flush()
            db.refresh(ride)
            return ride

        db.rollback()
        ride = db.query(Ride).filter(Ride.id == ride_id).first()
        if not ride:
            raise RideNotFound
        if ride.driver_id is not None:
            raise RideAlreadyClaimed
        if not can_driver_accept_ride(DriverStatus.AVAILABLE, ride.status):
            raise RideNotAvailable
        raise RideNotAvailable


def get_active_dispatch_policy() -> BaseDispatchPolicy:
    return OpenBoardDispatchPolicy()
