"""
Rider-side ride lifecycle (Stage 3 polish).

Endpoints (all customer-only):
* `POST /rides/` — create a ride request. Owner is the authenticated customer (`customer_id`).
* `POST /rides/{ride_id}/cancel` — cancel an owned ride from `requested` or `accepted` only.

Driver-side views still reflect cancellation: a ride that was already `accepted` keeps its
`driver_id` so the driver's `my-rides` shows status=`cancelled` with `cancelled_at` and
`lifecycle_reason`. Driver-side transitions reject the cancelled ride by state.
"""
import asyncio
import json
from datetime import datetime
from typing import Optional, Union

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.ride import Ride
from models.user import UserRole
from services.datetime_utils import utc_now_naive
from routes.drivers import ride_to_view
from schemas.rider_rides import (
    RiderCancelBody,
    RiderRideCreate,
    RiderRideResponse,
)
from schemas.rides import RideActionRequest
from services.ledger import record_ledger_entry
from services.lifecycle import (
    InvalidRideTransition,
    RideAction,
    RideStatus,
    next_ride_status,
    normalize_ride_status,
    to_storage_ride_status,
)
from services.metrics import record_event
from services.map_route_foundation import apply_map_foundation_defaults, apply_route_estimate, stamp_route_calculated
from services.ride_pricing import quote_ride_pricing
from services.route_snapshots import SNAPSHOT_ROLE_QUOTE, create_route_snapshot
from services.routing_service import route as routing_route
from services.auth_errors import auth_error_detail
from services.rbac import AuthPrincipal, load_principal_user, require_role, resolve_principal_from_bearer
from services.ride_dispatch_cascade import start_dispatch_for_ride
from services.ride_pool_broadcast import POOL_EVENT_CANCELLED, POOL_EVENT_CREATED, emit_pool_delta
from services.transition_errors import invalid_state_transition_detail, target_status_for_action


router = APIRouter(prefix="/rides", tags=["rider-rides"])
RIDER_ACCESS = require_role("rider")


def rider_sse_access(
    authorization: str | None = Header(default=None),
    access_token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> AuthPrincipal:
    if authorization:
        principal = resolve_principal_from_bearer(authorization)
    elif access_token and access_token.strip():
        principal = resolve_principal_from_bearer(f"Bearer {access_token.strip()}")
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=auth_error_detail("unauthenticated", "Missing bearer token"),
        )
    if principal.role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=auth_error_detail("forbidden", "rider access required"),
        )
    return load_principal_user(db, principal)

def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


@router.post("/", response_model=RiderRideResponse, response_model_exclude_none=True)
def create_ride(
    body: RiderRideCreate,
    customer: AuthPrincipal = Depends(RIDER_ACCESS),
    db: Session = Depends(get_db),
):
    customer = load_principal_user(db, customer)
    name = (body.customer_name or "").strip() or customer.name
    ride = Ride(
        customer_name=name,
        customer_id=customer.id,
        status=to_storage_ride_status(RideStatus.REQUESTED),
        pickup_location=(body.pickup_location or None),
        destination=(body.dropoff_location or body.destination or None),
        pickup_latitude=body.pickup_latitude,
        pickup_longitude=body.pickup_longitude,
        dropoff_latitude=body.dropoff_latitude,
        dropoff_longitude=body.dropoff_longitude,
        distance=body.distance_km if body.distance_km is not None else 0.0,
        duration=body.duration_minutes if body.duration_minutes is not None else 0,
    )
    apply_map_foundation_defaults(ride)
    estimate = None
    origin = None
    destination = None
    if (
        body.pickup_latitude is not None
        and body.pickup_longitude is not None
        and body.dropoff_latitude is not None
        and body.dropoff_longitude is not None
    ):
        origin = (body.pickup_latitude, body.pickup_longitude)
        destination = (body.dropoff_latitude, body.dropoff_longitude)
        estimate = routing_route(origin, destination)
        apply_route_estimate(ride, estimate)
    elif body.distance_km is not None or body.duration_minutes is not None:
        stamp_route_calculated(ride)
    db.add(ride)
    db.flush()
    pricing_row = quote_ride_pricing(
        db,
        ride_id=ride.id,
        distance_km=ride.distance or 0.0,
        duration_minutes=ride.duration or 0,
    )
    create_route_snapshot(
        db,
        ride=ride,
        route_result=estimate,
        snapshot_role=SNAPSHOT_ROLE_QUOTE,
        pricing=pricing_row,
        provenance={
            "source": "rider_create",
            "estimate_skipped": estimate is None,
        },
        origin=origin,
        destination=destination,
    )
    record_event(
        db,
        entity_type="ride",
        entity_id=ride.id,
        event_type="ride.created",
        actor_id=customer.id,
        payload={"source": "rider"},
    )
    start_dispatch_for_ride(db, ride.id)
    db.commit()
    db.refresh(ride)
    created_view = ride_to_view(ride, db=db)
    emit_pool_delta(
        event=POOL_EVENT_CREATED,
        ride_id=ride.id,
        ride=created_view.model_dump(mode="json"),
        removed=False,
    )
    return {
        "message": f"Ride {ride.id} created",
        "ride": created_view,
    }


@router.post("/{ride_id}/cancel", response_model=RiderRideResponse, response_model_exclude_none=True)
def cancel_ride(
    ride_id: int,
    customer: AuthPrincipal = Depends(RIDER_ACCESS),
    db: Session = Depends(get_db),
    body: Union[RiderCancelBody, None] = Body(default=None),
):
    customer = load_principal_user(db, customer)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.customer_id != customer.id:
        # Treat ownership mismatch as 403 — the rider may know the id exists but cannot act on it.
        raise HTTPException(status_code=403, detail="Not your ride")

    reason = (body.reason.strip() if body and body.reason else None) if body else None
    from_status = normalize_ride_status(ride.status).value
    try:
        ride.status = to_storage_ride_status(next_ride_status(ride.status, RideAction.CANCEL, UserRole.CUSTOMER))
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
    # Preserve driver_id when present so the driver sees the cancellation in `my-rides`.
    from services.ride_lifecycle_events import record_ride_lifecycle_event

    record_ride_lifecycle_event(
        db,
        ride_id=ride_id,
        event_type="ride.cancelled",
        from_state=from_status,
        to_state=RideStatus.CANCELLED,
        reason=reason or "customer_cancel",
        actor="customer",
        actor_id=customer.id,
    )
    if ride.driver_id is not None:
        record_ledger_entry(
            db,
            event_type="claim_released",
            ride_id=ride_id,
            actor_id=customer.id,
            driver_id=ride.driver_id,
            outcome=RideStatus.CANCELLED.value,
            reason=reason,
            payload={"released_by": "rider_cancel"},
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
    return {
        "message": f"Ride {ride_id} cancelled",
        "ride": ride_to_view(ride, db=db),
    }


@router.get("/{ride_id}", response_model=RiderRideResponse, response_model_exclude_none=True)
def get_ride(
    ride_id: int,
    customer: AuthPrincipal = Depends(RIDER_ACCESS),
    db: Session = Depends(get_db),
):
    customer = load_principal_user(db, customer)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.customer_id != customer.id:
        raise HTTPException(status_code=403, detail="Not your ride")
    return {
        "message": f"Ride {ride_id} fetched",
        "ride": ride_to_view(ride, db=db),
    }


@router.get("/{ride_id}/stream")
async def stream_ride_status(
    ride_id: int,
    request: Request,
    customer: AuthPrincipal = Depends(rider_sse_access),
    db: Session = Depends(get_db),
):
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.customer_id != customer.id:
        raise HTTPException(status_code=403, detail="Not your ride")

    async def event_generator():
        last_status = None
        while True:
            if await request.is_disconnected():
                break
            db.expire_all()
            latest = db.query(Ride).filter(Ride.id == ride_id).first()
            if not latest:
                break
            normalized_status = normalize_ride_status(latest.status).value
            if normalized_status != last_status:
                last_status = normalized_status
                payload = {"ride_id": ride_id, "status": normalized_status}
                yield f"data: {json.dumps(payload)}\n\n"
            if normalized_status in {RideStatus.COMPLETED.value, RideStatus.CANCELLED.value}:
                break
            await asyncio.sleep(2.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{ride_id}/action", response_model=RiderRideResponse, response_model_exclude_none=True)
def act_on_ride(
    ride_id: int,
    request: RideActionRequest,
    customer: AuthPrincipal = Depends(RIDER_ACCESS),
    db: Session = Depends(get_db),
):
    """Rider action endpoint.

    Invalid action names are rejected by Pydantic as 422 before handler code runs.
    The only rider action supported today is `cancel`.
    """
    if request.action != RideAction.CANCEL:
        raise HTTPException(status_code=400, detail="Unsupported rider action")
    return cancel_ride(ride_id=ride_id, customer=customer, db=db, body=None)
