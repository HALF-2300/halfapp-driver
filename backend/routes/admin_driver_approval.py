"""Admin ops skeleton: driver approval (DRIVER-002) + rides visibility (ADMIN-001)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.driver_approval import DriverApproval, DriverApprovalStatus
from models.ride import Ride
from models.user import User, UserRole
from services.datetime_utils import utc_now_naive
from services.driver_approval import approval_public_dict, set_driver_approval
from services.lifecycle import RideStatus, to_storage_ride_status
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


def _driver_admin_row(db: Session, driver: User) -> dict:
    approval = db.query(DriverApproval).filter(DriverApproval.driver_id == driver.id).first()
    return {
        "id": driver.id,
        "email": driver.email,
        "name": driver.name,
        "license_no": driver.license_no,
        "is_active": driver.is_active,
        "created_at": driver.created_at,
        "approval": approval_public_dict(approval),
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
        "completed_at": ride.completed_at,
        "lifecycle_reason": ride.lifecycle_reason,
        "notes": ride.notes,
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
