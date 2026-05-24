from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from services.datetime_utils import utc_now_naive
from models.driver_approval import DriverApproval, DriverApprovalStatus
from models.user import User, UserRole
from models.ride import Ride
from services.driver_approval import approval_public_dict, set_driver_approval
from services.lifecycle import RideStatus, to_storage_ride_status
from services.ride_pricing import get_ride_pricing
from services.v01_lifecycle import resolve_v01_lifecycle_status
from services.rbac import AuthPrincipal, load_principal_user, require_role

router = APIRouter(prefix="/admin", tags=["admin"])
ADMIN_ACCESS = require_role("admin")

@router.get("/users")
def list_users(admin_user: AuthPrincipal = Depends(ADMIN_ACCESS), db: Session = Depends(get_db)):
    load_principal_user(db, admin_user)
    users = db.query(User).all()
    return [{
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "license_no": user.license_no,
        "is_active": user.is_active,
        "created_at": user.created_at
    } for user in users]

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
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    load_principal_user(db, admin_user)
    query = db.query(User).filter(User.role == UserRole.DRIVER)
    if status:
        normalized = status.strip().lower()
        try:
            DriverApprovalStatus(normalized)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid approval status filter") from exc
        query = query.join(DriverApproval, DriverApproval.driver_id == User.id).filter(
            DriverApproval.status == DriverApprovalStatus(normalized)
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
        raise HTTPException(status_code=400, detail="Invalid approval status") from exc
    if new_status == DriverApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Cannot set approval status back to pending via API")
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
    return _driver_admin_row(db, driver) | {"approval": approval_public_dict(approval)}

@router.get("/rides")
def list_all_rides(admin_user: AuthPrincipal = Depends(ADMIN_ACCESS), db: Session = Depends(get_db)):
    """v0.1 ops view — status, rider/driver ids, integer-cent ledger summary (no analytics)."""
    load_principal_user(db, admin_user)
    rides = db.query(Ride).order_by(Ride.id.desc()).all()
    rows = []
    for ride in rides:
        pricing = get_ride_pricing(db, ride.id)
        entry = {
            "id": ride.id,
            "customer_name": ride.customer_name,
            "rider_id": ride.customer_id,
            "driver_id": ride.driver_id,
            "status": ride.status,
            "v01_lifecycle_status": resolve_v01_lifecycle_status(ride, pricing),
        }
        if pricing:
            entry["pricing"] = {
                "driver_shareable_fare_cents": pricing.driver_shareable_fare_cents,
                "driver_ride_payout_cents": pricing.driver_ride_payout_cents or pricing.driver_commission_cents,
                "platform_commission_cents": pricing.platform_commission_cents,
                "platform_revenue_cents": pricing.platform_revenue_cents or pricing.platform_earnings_cents,
                "customer_total_cents": pricing.customer_total_cents or pricing.total_rider_charge_cents,
                "financial_locked": bool(pricing.financial_locked),
            }
        rows.append(entry)
    return rows

@router.post("/users/{user_id}/toggle-active")
def toggle_user_active(user_id: int, admin_user: AuthPrincipal = Depends(ADMIN_ACCESS), db: Session = Depends(get_db)):
    load_principal_user(db, admin_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    db.commit()
    return {"message": f"User {user.email} is now {'active' if user.is_active else 'inactive'}"}

@router.get("/analytics/overview")
def get_system_analytics(admin_user: AuthPrincipal = Depends(ADMIN_ACCESS), db: Session = Depends(get_db)):
    load_principal_user(db, admin_user)
    # Get all users and rides for analytics
    all_users = db.query(User).all()
    all_rides = db.query(Ride).all()
    
    # Calculate comprehensive statistics
    total_users = len(all_users)
    total_drivers = len([u for u in all_users if u.role == UserRole.DRIVER])
    active_drivers = len([u for u in all_users if u.role == UserRole.DRIVER and u.is_active])
    total_customers = len([u for u in all_users if u.role == UserRole.CUSTOMER])
    
    completed_rides = [r for r in all_rides if r.status == to_storage_ride_status(RideStatus.COMPLETED)]
    total_revenue = sum(ride.fare_amount or 0 for ride in completed_rides)
    
    # Recent activity (last 7 days)
    from datetime import timedelta
    week_ago = utc_now_naive() - timedelta(days=7)
    recent_rides = [r for r in completed_rides if r.completed_at and r.completed_at >= week_ago]
    weekly_revenue = sum(ride.fare_amount or 0 for ride in recent_rides)
    
    return {
        "system_overview": {
            "total_users": total_users,
            "total_drivers": total_drivers,
            "active_drivers": active_drivers,
            "total_customers": total_customers,
            "total_rides": len(all_rides),
            "completed_rides": len(completed_rides),
            "total_revenue": round(total_revenue, 2),
            "weekly_revenue": round(weekly_revenue, 2),
            "average_ride_value": round(total_revenue / len(completed_rides), 2) if completed_rides else 0
        },
        "ride_status_breakdown": {
            "requested": len([r for r in all_rides if r.status == to_storage_ride_status(RideStatus.REQUESTED)]),
            "accepted": len([r for r in all_rides if r.status == to_storage_ride_status(RideStatus.ACCEPTED)]),
            "completed": len([r for r in all_rides if r.status == to_storage_ride_status(RideStatus.COMPLETED)]),
            "cancelled": len([r for r in all_rides if r.status == to_storage_ride_status(RideStatus.CANCELLED)])
        }
    }

@router.get("/analytics/driver-performance")
def get_driver_performance_analytics(admin_user: AuthPrincipal = Depends(ADMIN_ACCESS), db: Session = Depends(get_db)):
    load_principal_user(db, admin_user)
    drivers = db.query(User).filter(User.role == UserRole.DRIVER).all()
    driver_stats = []
    
    for driver in drivers:
        driver_rides = db.query(Ride).filter(Ride.driver_id == driver.id).all()
        completed_rides = [r for r in driver_rides if r.status == to_storage_ride_status(RideStatus.COMPLETED)]
        
        total_earnings = sum(ride.fare_amount or 0 for ride in completed_rides)
        total_distance = sum(ride.distance or 0 for ride in completed_rides)
        avg_rating = sum(ride.rating or 0 for ride in completed_rides if ride.rating) / len([r for r in completed_rides if r.rating]) if any(ride.rating for ride in completed_rides) else 0
        
        driver_stats.append({
            "driver_id": driver.id,
            "driver_name": driver.name,
            "driver_email": driver.email,
            "license_no": driver.license_no,
            "is_active": driver.is_active,
            "performance": {
                "total_rides": len(driver_rides),
                "completed_rides": len(completed_rides),
                "completion_rate": round(len(completed_rides) / len(driver_rides) * 100, 2) if driver_rides else 0,
                "total_earnings": round(total_earnings, 2),
                "total_distance": round(total_distance, 2),
                "average_rating": round(avg_rating, 2),
                "earnings_per_ride": round(total_earnings / len(completed_rides), 2) if completed_rides else 0
            }
        })
    
    # Sort by total earnings (top performers first)
    driver_stats.sort(key=lambda x: x["performance"]["total_earnings"], reverse=True)
    
    return {
        "driver_analytics": driver_stats,
        "summary": {
            "top_earner": driver_stats[0]["driver_name"] if driver_stats else "No data",
            "average_completion_rate": round(sum(d["performance"]["completion_rate"] for d in driver_stats) / len(driver_stats), 2) if driver_stats else 0,
            "total_platform_earnings": round(sum(d["performance"]["total_earnings"] for d in driver_stats), 2)
        }
    }

@router.get("/analytics/earnings-report")
def get_earnings_report(admin_user: AuthPrincipal = Depends(ADMIN_ACCESS), db: Session = Depends(get_db)):
    load_principal_user(db, admin_user)
    completed_rides = db.query(Ride).filter(Ride.status == to_storage_ride_status(RideStatus.COMPLETED)).all()
    
    # Group earnings by time periods
    from datetime import timedelta
    now = utc_now_naive()
    
    # Today's earnings
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_rides = [r for r in completed_rides if r.completed_at and r.completed_at >= today_start]
    today_revenue = sum(ride.fare_amount or 0 for ride in today_rides)
    
    # This week's earnings
    week_start = now - timedelta(days=7)
    week_rides = [r for r in completed_rides if r.completed_at and r.completed_at >= week_start]
    week_revenue = sum(ride.fare_amount or 0 for ride in week_rides)
    
    # This month's earnings
    month_start = now - timedelta(days=30)
    month_rides = [r for r in completed_rides if r.completed_at and r.completed_at >= month_start]
    month_revenue = sum(ride.fare_amount or 0 for ride in month_rides)
    
    # All time earnings
    total_revenue = sum(ride.fare_amount or 0 for ride in completed_rides)
    
    return {
        "earnings_report": {
            "today": {
                "revenue": round(today_revenue, 2),
                "rides": len(today_rides),
                "average_per_ride": round(today_revenue / len(today_rides), 2) if today_rides else 0
            },
            "this_week": {
                "revenue": round(week_revenue, 2),
                "rides": len(week_rides),
                "average_per_ride": round(week_revenue / len(week_rides), 2) if week_rides else 0
            },
            "this_month": {
                "revenue": round(month_revenue, 2),
                "rides": len(month_rides),
                "average_per_ride": round(month_revenue / len(month_rides), 2) if month_rides else 0
            },
            "all_time": {
                "revenue": round(total_revenue, 2),
                "rides": len(completed_rides),
                "average_per_ride": round(total_revenue / len(completed_rides), 2) if completed_rides else 0
            }
        },
        "revenue_trends": {
            "daily_growth": round(((today_revenue - (week_revenue - today_revenue) / 6) / ((week_revenue - today_revenue) / 6) * 100), 2) if week_revenue > today_revenue else 0,
            "weekly_growth": round(((week_revenue - (month_revenue - week_revenue) / 3) / ((month_revenue - week_revenue) / 3) * 100), 2) if month_revenue > week_revenue else 0
        }
    }