"""Admin ops skeleton: driver approval (DRIVER-002) + rides visibility (ADMIN-001)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models.driver_approval import DriverApproval, DriverApprovalStatus
from models.ride import Ride
from models.user import User, UserRole
from services.claim_eligibility import driver_active_ride_id
from services.datetime_utils import utc_now_naive
from services.driver_approval import approval_public_dict, set_driver_approval
from services.lifecycle import (
    InvalidRideTransition,
    RideAction,
    RideStatus,
    next_ride_status,
    normalize_ride_status,
    to_storage_ride_status,
)
from services.transition_errors import invalid_state_transition_detail, target_status_for_action
from services.ledger import append_marketplace_event, record_ledger_entry
from services.presence import derive_effective_presence, get_or_create_presence, presence_to_dict
from services.ride_audit import _lifecycle_events_block
from services.ride_payment import fail_payment_for_ride, get_ride_payment, payment_to_dict, authorize_payment_for_ride
from services.ride_pool_broadcast import POOL_EVENT_CANCELLED, POOL_EVENT_CLAIMED, emit_pool_delta
from services.ride_pricing import get_ride_pricing
from services.ride_settlement import list_settlement_entries, settlement_summary_for_ride
from services.route_snapshots import list_route_snapshots_for_ride
from services.v01_lifecycle import resolve_v01_lifecycle_status
from services.rbac import AuthPrincipal, load_principal_user, require_role

router = APIRouter(prefix="/admin", tags=["admin"])
ADMIN_ACCESS = require_role("admin")


class DriverApprovalPatchBody(BaseModel):
    status: str = Field(..., description="approved | rejected | suspended")
    reason: str | None = None


class DriverReadinessPatchBody(BaseModel):
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_year: int | None = Field(default=None, ge=1900, le=2100)
    license_plate: str | None = None
    insurance_policy: str | None = None
    insurance_expires_at: datetime | None = None
    vehicle_ready: bool | None = None
    reason: str | None = Field(default=None, max_length=500)


def _driver_admin_row(db: Session, driver: User) -> dict:
    approval = db.query(DriverApproval).filter(DriverApproval.driver_id == driver.id).first()
    presence = derive_effective_presence(get_or_create_presence(db, driver))
    active_ride_id = driver_active_ride_id(db, driver.id)
    presence_dict = presence_to_dict(presence)
    approval_dict = approval_public_dict(approval)
    return {
        "id": driver.id,
        "email": driver.email,
        "name": driver.name,
        "license_no": driver.license_no,
        "vehicle": {
            "make": driver.vehicle_make,
            "model": driver.vehicle_model,
            "year": driver.vehicle_year,
            "plate": driver.license_plate,
            "ready": bool(driver.vehicle_ready),
        },
        "insurance": {
            "policy": driver.insurance_policy,
            "expires_at": driver.insurance_expires_at.isoformat() if driver.insurance_expires_at else None,
        },
        "readiness": {
            "license_present": bool(driver.license_no),
            "vehicle_info_present": bool(driver.vehicle_make and driver.vehicle_model and driver.license_plate),
            "vehicle_ready": bool(driver.vehicle_ready),
            "insurance_policy_present": bool(driver.insurance_policy),
            "insurance_expires_at": driver.insurance_expires_at.isoformat() if driver.insurance_expires_at else None,
            "approval_status": approval_dict["status"],
        },
        "is_active": driver.is_active,
        "created_at": driver.created_at,
        "approval": approval_dict,
        "presence": presence_dict,
        "online": presence_dict["effective_state"] == "available",
        "active_ride_id": active_ride_id,
        "availability_label": "in_ride" if active_ride_id else ("available" if presence_dict["effective_state"] == "available" else "offline"),
    }


@router.get("/drivers")
def list_drivers(
    status: str | None = Query(default=None),
    approval_status: str | None = Query(default=None),
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    load_principal_user(db, admin_user)
    query = db.query(User).filter(User.role == UserRole.DRIVER)
    filter_status = approval_status or status
    if filter_status:
        normalized = filter_status.strip().lower()
        try:
            DriverApprovalStatus(normalized)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={"error": "invalid_approval_status", "message": "Invalid approval status filter"},
            ) from exc
        query = query.join(DriverApproval, DriverApproval.driver_id == User.id).filter(
            DriverApproval.status == normalized
        )
    drivers = query.order_by(User.id.desc()).all()
    return [_driver_admin_row(db, driver) for driver in drivers]


@router.patch("/drivers/{driver_id}/readiness")
def patch_driver_readiness(
    driver_id: int,
    body: DriverReadinessPatchBody,
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    admin = load_principal_user(db, admin_user)
    driver = db.query(User).filter(User.id == driver_id, User.role == UserRole.DRIVER).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    if body.vehicle_make is not None:
        driver.vehicle_make = _clean(body.vehicle_make)
    if body.vehicle_model is not None:
        driver.vehicle_model = _clean(body.vehicle_model)
    if body.vehicle_year is not None:
        driver.vehicle_year = body.vehicle_year
    if body.license_plate is not None:
        driver.license_plate = _clean(body.license_plate)
    if body.insurance_policy is not None:
        driver.insurance_policy = _clean(body.insurance_policy)
    if body.insurance_expires_at is not None:
        expires = body.insurance_expires_at
        driver.insurance_expires_at = expires.replace(tzinfo=None) if expires.tzinfo else expires
    if body.vehicle_ready is not None:
        driver.vehicle_ready = bool(body.vehicle_ready)

    if body.reason:
        append_marketplace_event(
            db,
            event_type="driver_readiness_reviewed",
            entity_type="driver",
            entity_id=driver.id,
            actor_id=admin.id,
            driver_id=driver.id,
            payload={
                "insurance_expires_at": driver.insurance_expires_at.isoformat()
                if driver.insurance_expires_at
                else None,
                "outcome": "vehicle_ready" if driver.vehicle_ready else "vehicle_not_ready",
                "reason": body.reason.strip(),
                "vehicle_ready": bool(driver.vehicle_ready),
            },
        )

    db.commit()
    db.refresh(driver)
    return {"message": "Driver readiness updated", "driver": _driver_admin_row(db, driver)}


@router.patch("/drivers/{driver_id}/approval")
def patch_driver_approval(
    driver_id: int,
    body: DriverApprovalPatchBody,
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    admin = load_principal_user(db, admin_user)
    try:
        new_status = DriverApprovalStatus(body.status.strip().lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_approval_status", "message": "status must be approved, rejected, or suspended"},
        ) from exc
    if new_status == DriverApprovalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_approval_status", "message": "Cannot set approval status back to pending via API"},
        )
    try:
        approval = set_driver_approval(
            db,
            driver_id=driver_id,
            status=new_status,
            reason=body.reason,
            reviewed_by=admin.id,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Driver not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    driver = db.query(User).filter(User.id == driver_id).one()
    pub = approval_public_dict(approval)
    return {
        "driver_id": driver_id,
        "status": pub["status"],
        "reason": pub["reason"],
        "reviewed_by": pub["reviewed_by"],
        "reviewed_at": pub["reviewed_at"],
        "driver": _driver_admin_row(db, driver),
        "approval": pub,
    }


_ACTIVE_ADMIN_STATUSES = frozenset(
    {
        to_storage_ride_status(RideStatus.ACCEPTED),
        to_storage_ride_status(RideStatus.DRIVER_ARRIVED),
        to_storage_ride_status(RideStatus.IN_PROGRESS),
    }
)


def _admin_ride_row(db: Session, ride: Ride) -> dict:
    pricing = get_ride_pricing(db, ride.id)
    snapshots = list_route_snapshots_for_ride(db, ride_id=ride.id)
    payment = get_ride_payment(db, ride.id)
    settlement = None
    if ride.status == to_storage_ride_status(RideStatus.COMPLETED):
        try:
            settlement = settlement_summary_for_ride(db, ride_id=ride.id)
        except Exception:
            settlement = None
    return {
        "id": ride.id,
        "customer_name": ride.customer_name,
        "rider_id": ride.customer_id,
        "driver_id": ride.driver_id,
        "status": ride.status,
        "v01_lifecycle_status": resolve_v01_lifecycle_status(ride, pricing),
        "created_at": ride.created_at,
        "accepted_at": ride.accepted_at,
        "completed_at": ride.completed_at,
        "cancelled_at": ride.cancelled_at,
        "lifecycle_reason": ride.lifecycle_reason,
        "notes": ride.notes,
        "payment_status": payment.status if payment else None,
        "payment_amount_cents": payment.amount_cents if payment else None,
        "pricing": (
            {
                "driver_shareable_fare_cents": pricing.driver_shareable_fare_cents,
                "driver_ride_payout_cents": pricing.driver_ride_payout_cents or pricing.driver_commission_cents,
                "platform_commission_cents": pricing.platform_commission_cents,
                "platform_revenue_cents": pricing.platform_revenue_cents or pricing.platform_earnings_cents,
                "customer_total_cents": pricing.customer_total_cents or pricing.total_rider_charge_cents,
                "financial_locked": bool(pricing.financial_locked),
            }
            if pricing
            else None
        ),
        "route_snapshot_ids": [row.id for row in snapshots],
        "settlement_entry_count": len(list_settlement_entries(db, ride_id=ride.id)),
        "settlement": settlement,
    }


def _admin_ride_detail(db: Session, ride: Ride) -> dict:
    payment = get_ride_payment(db, ride.id)
    row = _admin_ride_row(db, ride)
    row["payment"] = payment_to_dict(payment) if payment else None
    row["lifecycle_events"] = _lifecycle_events_block(db, ride=ride)
    return row


@router.get("/rides")
def list_admin_rides(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    load_principal_user(db, admin_user)
    query = db.query(Ride)
    normalized = (status or "").strip().lower()
    if normalized == "active":
        query = query.filter(Ride.status.in_(_ACTIVE_ADMIN_STATUSES))
        rides = query.order_by(Ride.id.desc()).all()
        return {"rides": [_admin_ride_row(db, ride) for ride in rides], "page": 1, "page_size": len(rides)}
    if normalized == "completed":
        query = query.filter(Ride.status == to_storage_ride_status(RideStatus.COMPLETED))
        total = query.count()
        rides = (
            query.order_by(Ride.completed_at.desc(), Ride.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {
            "rides": [_admin_ride_row(db, ride) for ride in rides],
            "page": page,
            "page_size": page_size,
            "total": total,
        }
    rides = query.order_by(Ride.id.desc()).limit(200).all()
    return {"rides": [_admin_ride_row(db, ride) for ride in rides], "page": 1, "page_size": len(rides)}


@router.get("/rides/{ride_id}")
def get_admin_ride(
    ride_id: int,
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    load_principal_user(db, admin_user)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    return _admin_ride_detail(db, ride)


class AdminCancelRideBody(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


@router.post("/rides/{ride_id}/cancel")
def admin_cancel_ride(
    ride_id: int,
    body: AdminCancelRideBody | None = None,
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    admin = load_principal_user(db, admin_user)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    reason = (body.reason.strip() if body and body.reason else None) or "ops_cancel"
    from_status = normalize_ride_status(ride.status).value
    try:
        ride.status = to_storage_ride_status(
            next_ride_status(ride.status, RideAction.CANCEL, UserRole.ADMIN)
        )
    except InvalidRideTransition as exc:
        raise HTTPException(
            status_code=409,
            detail=invalid_state_transition_detail(
                ride_id=ride_id,
                from_status=from_status,
                to_status=target_status_for_action(RideAction.CANCEL.value),
                message=str(exc),
            ),
        ) from exc

    ride.cancelled_at = utc_now_naive()
    ride.lifecycle_reason = reason
    from services.ride_lifecycle_events import record_ride_lifecycle_event

    record_ride_lifecycle_event(
        db,
        ride_id=ride_id,
        event_type="ride.cancelled",
        from_state=from_status,
        to_state=RideStatus.CANCELLED,
        reason=reason,
        actor="admin",
        actor_id=admin.id,
    )
    fail_payment_for_ride(db, ride)
    if ride.driver_id is not None:
        record_ledger_entry(
            db,
            event_type="claim_released",
            ride_id=ride_id,
            actor_id=admin.id,
            driver_id=ride.driver_id,
            outcome=RideStatus.CANCELLED.value,
            reason=reason,
            payload={"released_by": "ops_cancel"},
        )
    db.commit()
    db.refresh(ride)
    if from_status == RideStatus.REQUESTED.value or ride.driver_id is None:
        emit_pool_delta(
            event=POOL_EVENT_CANCELLED,
            ride_id=ride_id,
            ride=None,
            removed=True,
        )
    return {"message": f"Ride {ride_id} cancelled by ops", "ride": _admin_ride_detail(db, ride)}


class AdminAssignRideBody(BaseModel):
    driver_id: int = Field(..., ge=1)


@router.post("/rides/{ride_id}/assign")
def admin_assign_ride(
    ride_id: int,
    body: AdminAssignRideBody,
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    admin = load_principal_user(db, admin_user)
    driver = db.query(User).filter(User.id == body.driver_id, User.role == UserRole.DRIVER).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    from services.dispatch import RideAlreadyClaimed, RideNotAvailable, RideNotFound
    from services.ride_auto_assign import assign_ride_to_driver

    try:
        ride = assign_ride_to_driver(
            db,
            ride_id,
            body.driver_id,
            reason="ops_assigned",
            actor="admin",
            actor_id=admin.id,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "ride_not_found":
            raise HTTPException(status_code=404, detail="Ride not found") from exc
        if code == "ride_already_assigned":
            raise HTTPException(status_code=409, detail="Ride already has a driver assigned") from exc
        raise HTTPException(status_code=409, detail="Ride cannot be assigned in its current state") from exc
    except (RideNotFound,):
        raise HTTPException(status_code=404, detail="Ride not found") from None
    except (RideAlreadyClaimed,):
        raise HTTPException(status_code=409, detail="Ride already claimed") from None
    except (RideNotAvailable,):
        raise HTTPException(status_code=409, detail="Driver cannot claim this ride") from None

    authorize_payment_for_ride(db, ride)
    db.commit()
    db.refresh(ride)
    emit_pool_delta(
        event=POOL_EVENT_CLAIMED,
        ride_id=ride.id,
        ride=None,
        removed=True,
    )
    return {"message": f"Ride {ride_id} assigned to driver {body.driver_id}", "ride": _admin_ride_detail(db, ride)}


class RideSupportNoteBody(BaseModel):
    note: str = Field(..., min_length=1, max_length=4000)


@router.post("/rides/{ride_id}/notes")
def add_ride_support_note(
    ride_id: int,
    body: RideSupportNoteBody,
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    admin = load_principal_user(db, admin_user)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    stamp = utc_now_naive().isoformat()
    line = f"[{stamp} admin:{admin.id}] {body.note.strip()}"
    ride.notes = f"{ride.notes}\n{line}".strip() if ride.notes else line
    db.commit()
    db.refresh(ride)
    return {"ride_id": ride_id, "notes": ride.notes}
