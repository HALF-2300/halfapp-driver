from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import json
import queue as thread_queue
import random
from typing import Optional, Union

from config import is_ride_simulation_enabled
from database import get_db
from production_guards import SIMULATION_DISABLED_DETAIL
from services.dispatch import (
    BaseDispatchPolicy,
    RideAlreadyClaimed,
    RideNotAvailable,
    RideNotFound,
    get_active_dispatch_policy,
)
from services.datetime_utils import utc_now_naive
from services.ledger import record_ledger_entry
from services.lifecycle import (
    DriverStatus,
    DriverUnavailableForRide,
    InvalidRideTransition,
    NotificationType,
    RideAction,
    RideStatus,
    assert_driver_can_accept_ride,
    next_ride_status,
    normalize_ride_status,
    release_accepted_ride_to_pool,
    to_storage_ride_status,
)
from services.metrics import (
    RIDE_HIDE_TTL_SECONDS,
    dismiss_visible_ride,
    get_driver_insights,
    get_driver_performance_snapshot,
    record_accept_metrics,
    record_available_rides,
    record_claim_attempt,
    record_completed_metrics,
    record_event,
    record_metric,
    record_started_metrics,
    get_ride_transparency,
)
from services.auth_errors import auth_error_detail
from services.transition_errors import invalid_state_transition_detail, target_status_for_action
from services.ride_dispatch_cascade import (
    DISPATCH_TIMEOUT_SECONDS,
    refresh_open_dispatch_offers,
    record_dispatch_accepted,
    record_dispatch_declined,
    ride_visible_to_driver,
    sequential_dispatch_enabled,
    start_dispatch_for_ride,
)
from services.claim_eligibility import (
    DriverClaimIneligible,
    _BLOCKED_PROFILE_AVAILABILITY,
    assert_driver_eligible_for_claim,
    claim_block_uses_409,
    driver_active_ride_id,
    driver_claim_blocked_detail,
    driver_is_dispatch_eligible,
)
from services.transparency import build_driver_scoped_transparency, claim_conflict_detail
from services.presence import (
    derive_effective_presence,
    get_or_create_presence,
    presence_to_dict,
    record_heartbeat,
    set_presence_state,
    validate_presence_state,
)
from schemas.drivers import DriverLocationUpdateResponse, DriverMeStatusView, DriverStatusResponse
from services.driver_app_settings_service import (
    get_or_create_settings,
    settings_to_dict,
    update_settings,
)
from services.driver_idempotency import execute_idempotent_ride_write
from services.driver_in_app_notifications import notify_driver_in_app
from services.driver_profile_service import (
    get_or_create_profile,
    profile_to_dict,
    update_profile,
)
from services.driver_approval import (
    DriverApprovalDenied,
    approval_status_value,
    assert_driver_can_perform_ride_action,
    get_driver_approval,
)
from services.driver_status_service import (
    driver_status_to_dict,
    get_or_create_driver_status,
    persist_driver_location,
    set_driver_offline,
    set_driver_online,
)
from services.rbac import (
    AuthPrincipal,
    load_principal_user,
    require_role,
    resolve_principal_from_bearer,
)
from services.event_bus import event_bus
from services.ride_pool_broadcast import (
    POOL_EVENT_CANCELLED,
    POOL_EVENT_CLAIMED,
    POOL_EVENT_CREATED,
    RIDE_POOL_TOPIC,
    emit_pool_delta,
    format_sse_event,
)
from models.user import User, UserRole
from models.ride import Ride
from schemas.earnings import (
    DriverEarningsResponse,
    EarningsRecentRide,
    EarningsSummary,
)
from schemas.payment import DriverRidePaymentsResponse, RidePaymentResponse, RidePaymentView
from schemas.ride_lifecycle import (
    CompleteRideResponse,
    DeclineRideBody,
    RideDriverView,
    RideTransitionResponse,
)
from schemas.ride_pricing import CompleteRidePricingBody, RidePricingView
from services.map_route_foundation import (
    apply_map_foundation_defaults,
    apply_route_estimate,
    map_foundation_dict,
    stamp_route_calculated,
)
from services.ride_route_grounding import ground_ride_route
from services.v01_lifecycle import resolve_v01_lifecycle_status
from services.ride_pricing import (
    PricingLockedError,
    cents_to_display_dollars,
    finalize_ride_pricing,
    get_ride_pricing,
    quote_ride_pricing,
)
from services.routing_service import route as routing_route
from services.route_snapshots import (
    SNAPSHOT_ROLE_COMPLETE,
    SNAPSHOT_ROLE_QUOTE,
    create_route_snapshot,
    list_route_snapshots_for_ride,
    route_snapshot_public_view,
)
from services.route_snapshots_read import build_route_snapshots_driver_read
from services.payment_execution import (
    create_charge_intent_from_pricing,
    try_start_stripe_charge_for_ride,
)
from services.ride_settlement import (
    generate_settlement_entries,
    settlement_summary_for_ride,
)
from services.ride_audit import build_driver_ride_audit
from services.payment_reconciliation import (
    compute_driver_payment_reconciliation,
    enrich_reconciliation_with_payouts,
    list_driver_payment_executions,
    list_driver_payouts,
)
from models.ride_pricing import RidePricing

router = APIRouter(prefix="/drivers", tags=["drivers"])


def _raise_invalid_transition(
    *,
    ride_id: int,
    from_status: str,
    to_status: str,
    exc: InvalidRideTransition,
) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=invalid_state_transition_detail(
            ride_id=ride_id,
            from_status=from_status,
            to_status=to_status,
            message=str(exc),
        ),
    ) from exc
DRIVER_ACCESS = require_role("driver")

_STATUSES_PAST_POOL = frozenset(
    {
        to_storage_ride_status(RideStatus.ACCEPTED),
        to_storage_ride_status(RideStatus.DRIVER_ARRIVED),
        to_storage_ride_status(RideStatus.IN_PROGRESS),
        to_storage_ride_status(RideStatus.COMPLETED),
    }
)

_ACTIVE_DRIVER_RIDE_STATUSES = frozenset(
    {
        to_storage_ride_status(RideStatus.ACCEPTED),
        to_storage_ride_status(RideStatus.DRIVER_ARRIVED),
        to_storage_ride_status(RideStatus.IN_PROGRESS),
    }
)


class ActiveRideLifecycleView(BaseModel):
    current: str
    available_actions: list[str] = []
    history: list[dict] = []


class ActiveRideCustomerView(BaseModel):
    name: str
    phone_masked: str | None = None


class DriverActiveRideResponse(BaseModel):
    ride: RideDriverView | None = None
    lifecycle_stage: str | None = None
    navigation: dict | None = None
    lifecycle: ActiveRideLifecycleView | None = None
    route: dict | None = None
    customer: ActiveRideCustomerView | None = None


def _driver_sse_principal(
    authorization: str | None = Header(default=None),
    access_token: str | None = Query(default=None),
) -> AuthPrincipal:
    """EventSource cannot set Authorization; accept bearer header or ?access_token=."""
    if authorization:
        return resolve_principal_from_bearer(authorization)
    if access_token and access_token.strip():
        return resolve_principal_from_bearer(f"Bearer {access_token.strip()}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=auth_error_detail("unauthenticated", "Missing bearer token"),
    )


def driver_sse_access(
    authorization: str | None = Header(default=None),
    access_token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> AuthPrincipal:
    principal = _driver_sse_principal(authorization=authorization, access_token=access_token)
    if principal.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=auth_error_detail("forbidden", "driver access required"),
        )
    return load_principal_user(db, principal)


def _broadcast_pool_ride_created(db: Session, ride: Ride) -> None:
    view = ride_to_view(ride, db=db)
    emit_pool_delta(
        event=POOL_EVENT_CREATED,
        ride_id=ride.id,
        ride=view.model_dump(mode="json"),
        removed=False,
    )


def _broadcast_pool_ride_removed(*, ride_id: int, event: str) -> None:
    emit_pool_delta(event=event, ride_id=ride_id, ride=None, removed=True)


class DriverMeProfileOut(BaseModel):
    display_name: str | None = None
    phone_e164: str | None = None
    photo_url: str | None = None
    updated_at: str | None = None


class DriverMeProfileIn(BaseModel):
    display_name: str | None = None
    phone_e164: str | None = None
    photo_url: str | None = None


class DriverAppSettingsOut(BaseModel):
    units: str
    locale: str
    theme: str
    notif_push_enabled: bool
    notif_sound_enabled: bool
    notif_quiet_hours: dict | None = None
    updated_at: str | None = None


class DriverAppSettingsIn(BaseModel):
    units: str | None = None
    locale: str | None = None
    theme: str | None = None
    notif_push_enabled: bool | None = None
    notif_sound_enabled: bool | None = None
    notif_quiet_hours: dict | None = None


class DriverProfileUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    emergency_contact: str | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_year: int | None = None
    license_plate: str | None = None
    insurance_policy: str | None = None
    availability: str | None = None

    @field_validator("availability")
    @classmethod
    def availability_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            return DriverStatus(v).value
        except ValueError:
            allowed = ", ".join(status.value for status in DriverStatus)
            raise ValueError(f"availability must be one of: {allowed}")


class DriverMeStatusPatch(BaseModel):
    online: bool
    lat: float | None = None
    lng: float | None = None

    @field_validator("lat")
    @classmethod
    def lat_range(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < -90 or v > 90:
            raise ValueError("lat must be between -90 and 90")
        return v

    @field_validator("lng")
    @classmethod
    def lng_range(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < -180 or v > 180:
            raise ValueError("lng must be between -180 and 180")
        return v


class DriverMeLocationPatch(BaseModel):
    lat: float
    lng: float

    @field_validator("lat")
    @classmethod
    def lat_range(cls, v: float) -> float:
        if v < -90 or v > 90:
            raise ValueError("lat must be between -90 and 90")
        return v

    @field_validator("lng")
    @classmethod
    def lng_range(cls, v: float) -> float:
        if v < -180 or v > 180:
            raise ValueError("lng must be between -180 and 180")
        return v


class DriverTelemetryIn(BaseModel):
    lat: float
    lng: float
    speed_mps: float | None = None

    @field_validator("lat")
    @classmethod
    def lat_range(cls, v: float) -> float:
        if v < -90 or v > 90:
            raise ValueError("lat must be between -90 and 90")
        return v

    @field_validator("lng")
    @classmethod
    def lng_range(cls, v: float) -> float:
        if v < -180 or v > 180:
            raise ValueError("lng must be between -180 and 180")
        return v


class LocationUpdate(BaseModel):
    latitude: float
    longitude: float

    @field_validator("latitude")
    @classmethod
    def lat_range(cls, v: float) -> float:
        if v < -90 or v > 90:
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def lon_range(cls, v: float) -> float:
        if v < -180 or v > 180:
            raise ValueError("longitude must be between -180 and 180")
        return v


class DriverPresenceUpdate(BaseModel):
    state: str

    @field_validator("state")
    @classmethod
    def state_ok(cls, v: str) -> str:
        try:
            return validate_presence_state(v)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class HideRideBody(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class SimulationRideCreate(BaseModel):
    customer_name: str = "Simulation Rider"
    pickup_location: str = "Simulation Pickup"
    destination: str = "Simulation Destination"
    pickup_latitude: Optional[float] = Field(None, ge=-90, le=90)
    pickup_longitude: Optional[float] = Field(None, ge=-180, le=180)
    dropoff_latitude: Optional[float] = Field(None, ge=-90, le=90)
    dropoff_longitude: Optional[float] = Field(None, ge=-180, le=180)
    distance_km: Optional[float] = Field(
        None,
        description="Optional override; when omitted, distance comes from OSRM routing",
    )
    duration_minutes: Optional[int] = Field(
        None,
        description="Optional override; when omitted, duration comes from OSRM routing",
    )

    @field_validator("customer_name", "pickup_location", "destination")
    @classmethod
    def text_required(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("value cannot be empty")
        return cleaned

    @field_validator("distance_km")
    @classmethod
    def distance_range(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if v < 0 or v > 10_000:
            raise ValueError("distance_km must be between 0 and 10000")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def duration_range(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v < 0 or v > 24 * 60:
            raise ValueError("duration_minutes must be between 0 and 1440")
        return v


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def _pricing_to_view(row: RidePricing | None) -> RidePricingView | None:
    if row is None:
        return None
    locked_at = row.locked_at or row.fare_locked_at
    driver_payout = row.driver_ride_payout_cents or row.driver_commission_cents
    platform_rev = row.platform_revenue_cents or row.platform_earnings_cents
    customer_total = row.customer_total_cents or row.total_rider_charge_cents
    return RidePricingView(
        pricing_policy_id=row.pricing_policy_id,
        pricing_version=row.pricing_version,
        market_id=row.market_id,
        base_fare_cents=row.base_fare_cents or 0,
        distance_fare_cents=row.distance_fare_cents or 0,
        time_fare_cents=row.time_fare_cents or 0,
        wait_fee_cents=row.wait_fee_cents or 0,
        driver_shareable_fare_cents=row.driver_shareable_fare_cents,
        platform_service_fee_cents=row.platform_service_fee_cents,
        tip_cents=row.tip_cents,
        city_fee_cents=row.city_fee_cents,
        airport_fee_cents=row.airport_fee_cents,
        toll_cents=row.toll_cents,
        accessibility_fee_cents=row.accessibility_fee_cents,
        tax_cents=row.tax_cents,
        driver_commission_cents=driver_payout,
        driver_ride_payout_cents=driver_payout,
        platform_commission_cents=row.platform_commission_cents,
        driver_earnings_cents=row.driver_earnings_cents,
        driver_total_payout_cents=row.driver_earnings_cents,
        platform_earnings_cents=platform_rev,
        platform_revenue_cents=platform_rev,
        pass_through_total_cents=row.pass_through_total_cents,
        total_rider_charge_cents=customer_total,
        customer_total_cents=customer_total,
        financial_locked=bool(row.financial_locked),
        locked_at=_iso(locked_at),
        fare_locked_at=_iso(row.fare_locked_at),
    )


def ride_to_view(
    ride: Ride,
    dispatch_metadata: dict | None = None,
    db: Session | None = None,
) -> RideDriverView:
    dispatch_metadata = dispatch_metadata or {}
    pricing_row = get_ride_pricing(db, ride.id) if db is not None else None
    map_meta = map_foundation_dict(ride)
    fare_display = ride.fare_amount
    if pricing_row and pricing_row.driver_earnings_cents:
        fare_display = cents_to_display_dollars(pricing_row.driver_earnings_cents)
    assigned_driver_name = None
    if ride.driver_id is not None and db is not None:
        driver_row = db.query(User).filter(User.id == ride.driver_id).first()
        if driver_row is not None:
            assigned_driver_name = driver_row.name
    return RideDriverView(
        id=ride.id,
        rider_id=ride.customer_id,
        driver_id=ride.driver_id,
        assigned_driver_name=assigned_driver_name,
        customer_name=ride.customer_name,
        status=normalize_ride_status(ride.status).value,
        v01_lifecycle_status=resolve_v01_lifecycle_status(ride, pricing_row),
        pickup_location=ride.pickup_location,
        dropoff_location=ride.destination,
        destination=ride.destination,
        pickup_latitude=ride.pickup_latitude,
        pickup_longitude=ride.pickup_longitude,
        dropoff_latitude=ride.dropoff_latitude,
        dropoff_longitude=ride.dropoff_longitude,
        fare_amount=fare_display,
        driver_shareable_fare_cents=pricing_row.driver_shareable_fare_cents if pricing_row else None,
        driver_total_payout_cents=pricing_row.driver_earnings_cents if pricing_row else None,
        customer_total_cents=(
            (pricing_row.customer_total_cents or pricing_row.total_rider_charge_cents) if pricing_row else None
        ),
        platform_revenue_cents=(
            (pricing_row.platform_revenue_cents or pricing_row.platform_earnings_cents) if pricing_row else None
        ),
        distance_km=ride.distance,
        duration_minutes=ride.duration,
        created_at=_iso(ride.created_at),
        updated_at=_iso(ride.completed_at or ride.cancelled_at or ride.started_at or ride.arrived_pickup_at or ride.accepted_at),
        accepted_at=_iso(ride.accepted_at),
        arrived_pickup_at=_iso(ride.arrived_pickup_at),
        started_at=_iso(ride.started_at),
        completed_at=_iso(ride.completed_at),
        cancelled_at=_iso(ride.cancelled_at),
        lifecycle_reason=ride.lifecycle_reason,
        ride_visibility_id=dispatch_metadata.get("ride_visibility_id"),
        visibility_correlation_id=dispatch_metadata.get("visibility_correlation_id"),
        visibility_reason=dispatch_metadata.get("visibility_reason"),
        ordering_rank=dispatch_metadata.get("ordering_rank") or getattr(ride, "ordering_rank", None),
        ordering_score=dispatch_metadata.get("ordering_score") or getattr(ride, "ordering_score", None),
        why_this_rank=dispatch_metadata.get("why_this_rank") or getattr(ride, "why_this_rank", None),
        dispatch_policy_id=dispatch_metadata.get("dispatch_policy_id") or getattr(ride, "dispatch_policy_id", None),
        dispatch_policy_name=dispatch_metadata.get("dispatch_policy_name") or getattr(ride, "dispatch_policy_name", None),
        ordered_by=dispatch_metadata.get("ordered_by"),
        policy_version=dispatch_metadata.get("policy_version"),
        generated_at=_iso(dispatch_metadata.get("generated_at")),
        dispatch_expires_at=_iso(ride.dispatch_expires_at),
        dispatch_timeout_seconds=DISPATCH_TIMEOUT_SECONDS,
        pricing=_pricing_to_view(pricing_row),
        route_provider=map_meta["route_provider"],
        traffic_provider=map_meta["traffic_provider"],
        traffic_aware=map_meta["traffic_aware"],
        traffic_signal_aware=map_meta["traffic_signal_aware"],
        route_confidence=map_meta["route_confidence"],
        route_calculated_at=map_meta["route_calculated_at"],
        route_source=map_meta["route_source"],
        route_used_fallback=map_meta["route_used_fallback"],
        route_provider_confidence=map_meta["route_provider_confidence"],
        google_maps_fallback_enabled=map_meta["google_maps_fallback_enabled"],
        mapbox_traffic_enabled=map_meta["mapbox_traffic_enabled"],
    )


def _clear_active_leg(ride: Ride) -> None:
    ride.accepted_at = None
    ride.arrived_pickup_at = None
    ride.started_at = None


def _simulation_coordinate(value: Optional[float], base: float) -> float:
    if value is not None:
        return value
    return base + random.uniform(-0.03, 0.03)


@router.get("/")
def list_drivers(db: Session = Depends(get_db)):
    """Public driver directory (id, name, license) — intentionally unauthenticated for open-board MVP."""
    drivers = db.query(User).filter(User.role == UserRole.DRIVER).all()
    return [
        {
            "id": driver.id,
            "license_no": driver.license_no,
            "name": driver.name,
        }
        for driver in drivers
    ]


@router.get("/presence")
def get_driver_presence(driver_user: AuthPrincipal = Depends(DRIVER_ACCESS), db: Session = Depends(get_db)):
    driver_user = load_principal_user(db, driver_user)
    presence = derive_effective_presence(get_or_create_presence(db, driver_user))
    driver_user.availability = "available" if presence.effective_state == "available" else "offline"
    db.commit()
    return presence_to_dict(presence)


@router.put("/presence")
def update_driver_presence(
    body: DriverPresenceUpdate,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    try:
        presence = set_presence_state(db, driver_user, body.state)
    except DriverApprovalDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=auth_error_detail(exc.error_code, exc.message),
        ) from exc
    from services.driver_status_service import sync_from_presence

    sync_from_presence(db, driver_user, effective_state=presence.effective_state)
    record_event(
        db,
        entity_type="driver_presence",
        entity_id=driver_user.id,
        event_type="presence.changed",
        actor_id=driver_user.id,
        payload=presence_to_dict(presence),
    )
    db.commit()
    db.refresh(presence)
    return presence_to_dict(presence)


@router.get("/me/status", response_model=DriverMeStatusView)
def get_driver_me_status(driver_user: AuthPrincipal = Depends(DRIVER_ACCESS), db: Session = Depends(get_db)):
    """Durable online/offline state for cockpit refresh (DRIVER-001)."""
    driver_user = load_principal_user(db, driver_user)
    row = get_or_create_driver_status(db, driver_user)
    db.commit()
    return driver_status_to_dict(row)


@router.patch("/me/status", response_model=DriverMeStatusView)
def patch_driver_me_status(
    body: DriverMeStatusPatch,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    try:
        if body.online:
            if body.lat is None or body.lng is None:
                raise HTTPException(
                    status_code=400,
                    detail="lat and lng are required when going online",
                )
            row = set_driver_online(db, driver_user, lat=body.lat, lng=body.lng)
            from services.presence import set_presence_state

            set_presence_state(db, driver_user, "available")
        else:
            row = set_driver_offline(db, driver_user)
            from services.presence import set_presence_state

            set_presence_state(db, driver_user, "offline")
    except DriverApprovalDenied as exc:
        raise HTTPException(
            status_code=403,
            detail=auth_error_detail(exc.error_code, exc.message),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_event(
        db,
        entity_type="driver_status",
        entity_id=driver_user.id,
        event_type="status.changed",
        actor_id=driver_user.id,
        payload=driver_status_to_dict(row),
    )
    db.commit()
    db.refresh(row)
    return driver_status_to_dict(row)


@router.patch("/me/location", response_model=DriverMeStatusView)
def patch_driver_me_location(
    body: DriverMeLocationPatch,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    try:
        row = persist_driver_location(db, driver_user, lat=body.lat, lng=body.lng)
    except ValueError as exc:
        if str(exc) == "driver_offline":
            raise HTTPException(
                status_code=400,
                detail="Location updates are only allowed while the driver is online",
            ) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    from services.presence import record_heartbeat

    record_heartbeat(db, driver_user)
    db.commit()
    db.refresh(row)
    return driver_status_to_dict(row)


@router.post("/me/telemetry")
def post_driver_telemetry(
    body: DriverTelemetryIn,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """Ingest GPS speed sample for fleet-wide slow-zone heatmap (not municipal traffic)."""
    from models.driver_telemetry_point import DriverTelemetryPoint

    driver_user = load_principal_user(db, driver_user)
    db.add(
        DriverTelemetryPoint(
            driver_id=driver_user.id,
            lat=float(body.lat),
            lng=float(body.lng),
            speed_mps=float(body.speed_mps) if body.speed_mps is not None else None,
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/me/traffic-heatmap")
def get_fleet_traffic_heatmap(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    minutes: int = 10,
    precision: float = 0.002,
):
    """Slow zones from HalfApp driver GPS speeds (no TomTom/Mapbox key)."""
    from services.fleet_traffic_heatmap import build_fleet_traffic_heatmap

    load_principal_user(db, driver_user)
    if minutes < 1 or minutes > 120:
        raise HTTPException(status_code=400, detail="minutes_out_of_range")
    if precision < 0.0005 or precision > 0.02:
        raise HTTPException(status_code=400, detail="precision_out_of_range")
    return build_fleet_traffic_heatmap(db, minutes=minutes, precision=precision)


@router.post("/heartbeat")
def heartbeat_driver_presence(driver_user: AuthPrincipal = Depends(DRIVER_ACCESS), db: Session = Depends(get_db)):
    driver_user = load_principal_user(db, driver_user)
    presence = record_heartbeat(db, driver_user)
    record_event(
        db,
        entity_type="driver_presence",
        entity_id=driver_user.id,
        event_type="presence.heartbeat",
        actor_id=driver_user.id,
        payload=presence_to_dict(presence),
    )
    db.commit()
    db.refresh(presence)
    return presence_to_dict(presence)


def _query_driver_rides(
    db: Session,
    driver_id: int,
    *,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    q_text: Optional[str] = None,
    limit: int = 5000,
    offset: int = 0,
) -> list[Ride]:
    from services.driver_trips import build_trip_filters, list_driver_trips

    try:
        filters = build_trip_filters(
            from_date=from_date,
            to_date=to_date,
            status=status,
            q=q_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_date_filter") from exc
    items, _total = list_driver_trips(
        db, driver_id, filters, limit=limit, offset=offset
    )
    return items


def _driver_trip_filter_params(
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    q: Optional[str] = None,
):
    from services.driver_trips import build_trip_filters

    try:
        return build_trip_filters(
            from_date=from_date,
            to_date=to_date,
            status=status,
            q=q,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_date_filter") from exc


@router.get("/my-rides", response_model=list[RideDriverView])
def get_my_rides(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    q: Optional[str] = None,
):
    """Legacy list endpoint (full result set up to 5000 rows). Prefer GET /drivers/me/trips for pagination."""
    driver_user = load_principal_user(db, driver_user)
    rides = _query_driver_rides(
        db,
        driver_user.id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        q_text=q,
    )
    return [ride_to_view(ride, db=db) for ride in rides]


@router.get("/me/trips")
def get_my_trips_paginated(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    from services.driver_trips import list_driver_trips

    driver_user = load_principal_user(db, driver_user)
    filters = _driver_trip_filter_params(
        status=status, from_date=from_date, to_date=to_date, q=q
    )
    items, total = list_driver_trips(
        db, driver_user.id, filters, limit=limit, offset=offset
    )
    return {
        "items": [ride_to_view(ride, db=db) for ride in items],
        "total": total,
        "limit": max(1, min(int(limit), 5000)),
        "offset": max(0, int(offset)),
    }


def _stream_driver_trips_csv(db: Session, driver_id: int, filters, export_limit: int = 5000):
    from fastapi.responses import StreamingResponse
    import csv
    import io

    from services.driver_trips import CSV_HEADER, list_driver_trips, trip_row_for_csv

    items, _total = list_driver_trips(
        db, driver_id, filters, limit=export_limit, offset=0
    )

    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(CSV_HEADER)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for ride in items:
            view = ride_to_view(ride, db=db)
            writer.writerow(
                trip_row_for_csv(ride, fare_amount=view.fare_amount)
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="halfapp_trips.csv"'},
    )


@router.get("/me/trips/export.csv")
def export_my_trips_csv_v2(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
):
    driver_user = load_principal_user(db, driver_user)
    filters = _driver_trip_filter_params(
        status=status, from_date=from_date, to_date=to_date, q=q
    )
    return _stream_driver_trips_csv(db, driver_user.id, filters)


@router.get("/my-rides/export")
def export_my_rides_csv(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    q: Optional[str] = None,
):
    """Legacy CSV export path. Prefer GET /drivers/me/trips/export.csv."""
    driver_user = load_principal_user(db, driver_user)
    filters = _driver_trip_filter_params(
        status=status, from_date=from_date, to_date=to_date, q=q
    )
    response = _stream_driver_trips_csv(db, driver_user.id, filters)
    response.headers["Content-Disposition"] = 'attachment; filename="my-rides.csv"'
    return response


class RideMessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class SupportTicketIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    category: str = Field(default="trip_issue", max_length=64)


@router.get("/rides/{ride_id}/messages")
def list_ride_messages(
    ride_id: int,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    from services.ride_messages_service import list_ride_messages as list_msgs

    driver_user = load_principal_user(db, driver_user)
    items = list_msgs(db, ride_id=ride_id, driver_id=driver_user.id)
    if items is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    return {"items": items}


@router.post("/rides/{ride_id}/messages")
def post_ride_message(
    ride_id: int,
    body: RideMessageIn,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    from services.ride_messages_service import send_driver_ride_message

    driver_user = load_principal_user(db, driver_user)
    msg_id = send_driver_ride_message(
        db, ride_id=ride_id, driver_id=driver_user.id, body=body.body
    )
    if msg_id is None:
        raise HTTPException(status_code=404, detail="Ride not found or empty message")
    db.commit()
    return {"ok": True, "message_id": msg_id}


@router.get("/rides/{ride_id}/navigation")
def get_ride_navigation(
    ride_id: int,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    from services.navigation_service import get_navigation_bundle

    driver_user = load_principal_user(db, driver_user)
    bundle = get_navigation_bundle(db, ride_id=ride_id, driver_id=driver_user.id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    return bundle


@router.post("/rides/{ride_id}/support-ticket")
def post_ride_support_ticket(
    ride_id: int,
    body: SupportTicketIn,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    from models.driver_support_ticket import DriverSupportTicket

    driver_user = load_principal_user(db, driver_user)
    ride = db.query(Ride).filter(Ride.id == ride_id, Ride.driver_id == driver_user.id).first()
    if ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    row = DriverSupportTicket(
        ride_id=ride_id,
        driver_id=driver_user.id,
        category=(body.category or "trip_issue").strip()[:64],
        message=body.message.strip()[:4000],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "ticket_id": row.id}


@router.get("/rides/{ride_id}/transparency")
def get_ride_dispatch_transparency(
    ride_id: int,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    proof = get_ride_transparency(db, ride_id=ride_id)
    if proof is None:
        raise HTTPException(status_code=404, detail="Ride not found")

    driver_saw_ride = any(item["driver_id"] == driver_user.id for item in proof["driver_visibility"])
    driver_attempted_claim = any(item["driver_id"] == driver_user.id for item in proof["claim_attempts"])
    driver_assigned = proof["assigned_driver_id"] == driver_user.id
    if not (driver_saw_ride or driver_attempted_claim or driver_assigned):
        raise HTTPException(status_code=403, detail="Dispatch proof is not available to this driver")

    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    driver_view = build_driver_scoped_transparency(proof, driver_id=driver_user.id, ride=ride)
    return {
        **driver_view,
        "dispatch_proof": proof,
    }


def _driver_can_access_ride_truth(
    db: Session,
    *,
    driver_user_id: int,
    ride_id: int,
) -> None:
    proof = get_ride_transparency(db, ride_id=ride_id)
    if proof is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    driver_saw_ride = any(item["driver_id"] == driver_user_id for item in proof["driver_visibility"])
    driver_attempted_claim = any(
        item["driver_id"] == driver_user_id for item in proof["claim_attempts"]
    )
    driver_assigned = proof["assigned_driver_id"] == driver_user_id
    if not (driver_saw_ride or driver_attempted_claim or driver_assigned):
        raise HTTPException(status_code=403, detail="Ride truth is not available to this driver")


@router.get("/rides/{ride_id}/route-snapshots")
def get_ride_route_snapshots(
    ride_id: int,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """Read-only route evidence for rides this driver may access (no mutation)."""
    driver_user = load_principal_user(db, driver_user)
    _driver_can_access_ride_truth(db, driver_user_id=driver_user.id, ride_id=ride_id)
    payload = build_route_snapshots_driver_read(db, ride_id=ride_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    return payload


@router.get("/rides/{ride_id}/settlement")
def get_ride_settlement(
    ride_id: int,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """Read-only settlement boundary for a completed ride (no payment execution)."""
    driver_user = load_principal_user(db, driver_user)
    _driver_can_access_ride_truth(db, driver_user_id=driver_user.id, ride_id=ride_id)
    return settlement_summary_for_ride(db, ride_id=ride_id)


@router.get("/rides/{ride_id}/audit")
def get_ride_audit(
    ride_id: int,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """Read-only trip audit: lifecycle, pricing, settlement obligations, ledger events, route truth."""
    driver_user = load_principal_user(db, driver_user)
    return build_driver_ride_audit(db, ride_id=ride_id, driver_user_id=driver_user.id)


def _list_available_rides_for_driver(
    db: Session,
    driver_user: User,
    policy: BaseDispatchPolicy,
) -> list[RideDriverView]:
    presence = derive_effective_presence(get_or_create_presence(db, driver_user))
    if presence.effective_state == "available":
        from services.driver_status_service import sync_from_presence, touch_heartbeat

        sync_from_presence(
            db,
            driver_user,
            effective_state=presence.effective_state,
            lat=driver_user.last_latitude,
            lng=driver_user.last_longitude,
        )
        touch_heartbeat(db, driver_user)
    if not driver_is_dispatch_eligible(
        db,
        driver=driver_user,
        effective_presence_state=presence.effective_state,
    ):
        return []
    refresh_open_dispatch_offers(db)
    rides = policy.get_available_rides(db, driver_id=driver_user.id, driver=driver_user)
    rides = [ride for ride in rides if ride_visible_to_driver(ride, driver_user.id)]
    metadata = record_available_rides(db, driver_id=driver_user.id, rides=rides)
    return [ride_to_view(ride, metadata.get(ride.id), db=db) for ride in rides]


@router.get("/available-rides", response_model=list[RideDriverView])
def get_available_rides(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    policy: BaseDispatchPolicy = Depends(get_active_dispatch_policy),
):
    driver_user = load_principal_user(db, driver_user)
    return _list_available_rides_for_driver(db, driver_user, policy)


@router.get("/available-rides/stream")
def stream_available_rides(
    driver_user: User = Depends(driver_sse_access),
    db: Session = Depends(get_db),
    policy: BaseDispatchPolicy = Depends(get_active_dispatch_policy),
):
    """Server-Sent Events stream: initial snapshot, then pool deltas (in-process v0.1)."""
    snapshot = _list_available_rides_for_driver(db, driver_user, policy)
    snapshot_payload = [view.model_dump(mode="json") for view in snapshot]

    def event_generator():
        sync_queue = event_bus.subscribe_sync(RIDE_POOL_TOPIC)
        try:
            yield format_sse_event("snapshot", snapshot_payload)
            while True:
                try:
                    payload = sync_queue.get(timeout=15.0)
                    yield format_sse_event("delta", json.loads(payload))
                except thread_queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            event_bus.unsubscribe_sync(RIDE_POOL_TOPIC, sync_queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/me/active-ride", response_model=DriverActiveRideResponse)
def get_my_active_ride(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """Current accepted / at-pickup / in-progress ride for cockpit session recovery."""
    from services.active_ride_recovery import build_active_ride_recovery
    from services.navigation_service import get_navigation_bundle

    driver_user = load_principal_user(db, driver_user)
    ride = (
        db.query(Ride)
        .filter(
            Ride.driver_id == driver_user.id,
            Ride.status.in_(_ACTIVE_DRIVER_RIDE_STATUSES),
        )
        .order_by(Ride.id.desc())
        .first()
    )
    if ride is None:
        return DriverActiveRideResponse(
            ride=None,
            lifecycle_stage=None,
            navigation=None,
            lifecycle=None,
            route=None,
            customer=None,
        )

    view = ride_to_view(ride, db=db)
    navigation = get_navigation_bundle(db, ride_id=ride.id, driver_id=driver_user.id)
    recovery = build_active_ride_recovery(db, ride=ride)
    return DriverActiveRideResponse(
        ride=view,
        lifecycle_stage=recovery["lifecycle_stage"],
        navigation=navigation,
        lifecycle=recovery["lifecycle"],
        route=recovery["route"],
        customer=recovery["customer"],
    )


@router.post("/simulate-ride", response_model=RideTransitionResponse)
def create_simulation_ride(
    body: SimulationRideCreate,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """Create a backend-owned requested ride for driver-only MVP simulations.

    This keeps the cockpit demo truthful: even simulated requests enter the
    normal backend lifecycle before the driver accepts/completes them.

    Requires ``HALFAPP_ENABLE_RIDE_SIMULATION=1`` (disabled by default in production).
    """
    if not is_ride_simulation_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=SIMULATION_DISABLED_DETAIL,
        )
    driver_user = load_principal_user(db, driver_user)
    base_lat = 45.523064
    base_lng = -122.676483

    pickup_lat = _simulation_coordinate(body.pickup_latitude, base_lat)
    pickup_lng = _simulation_coordinate(body.pickup_longitude, base_lng)
    dropoff_lat = _simulation_coordinate(body.dropoff_latitude, base_lat)
    dropoff_lng = _simulation_coordinate(body.dropoff_longitude, base_lng)
    ride = Ride(
        customer_name=body.customer_name,
        status=to_storage_ride_status(RideStatus.REQUESTED),
        pickup_location=body.pickup_location,
        destination=body.destination,
        pickup_latitude=pickup_lat,
        pickup_longitude=pickup_lng,
        dropoff_latitude=dropoff_lat,
        dropoff_longitude=dropoff_lng,
        distance=body.distance_km if body.distance_km is not None else 0.0,
        duration=body.duration_minutes if body.duration_minutes is not None else 0,
        lifecycle_reason="simulation",
    )
    apply_map_foundation_defaults(ride)
    estimate = ground_ride_route(ride)
    if body.distance_km is not None:
        ride.distance = body.distance_km
    if body.duration_minutes is not None:
        ride.duration = body.duration_minutes
    elif estimate and not ride.duration:
        ride.duration = estimate.duration_minutes
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
        provenance={"source": "driver_simulation"},
        origin=(pickup_lat, pickup_lng),
        destination=(dropoff_lat, dropoff_lng),
    )
    record_event(
        db,
        entity_type="ride",
        entity_id=ride.id,
        event_type="ride.created",
        actor_id=driver_user.id,
        payload={"source": "driver_simulation"},
    )
    start_dispatch_for_ride(db, ride.id)
    db.commit()
    db.refresh(ride)
    _broadcast_pool_ride_created(db, ride)
    return RideTransitionResponse(
        message=f"Simulation ride {ride.id} created",
        ride=ride_to_view(ride, db=db),
    )


@router.post("/accept-ride/{ride_id}", response_model=RideTransitionResponse)
def accept_ride(
    ride_id: int,
    request: Request,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    policy: BaseDispatchPolicy = Depends(get_active_dispatch_policy),
):
    driver_user = load_principal_user(db, driver_user)
    return execute_idempotent_ride_write(
        request,
        db,
        driver_user.id,
        "drivers.accept-ride",
        "accept",
        ride_id,
        lambda: _accept_ride_impl(ride_id, driver_user, db, policy),
        RideTransitionResponse,
    )


def _accept_ride_impl(
    ride_id: int,
    driver_user,
    db: Session,
    policy: BaseDispatchPolicy,
):
    profile_availability = driver_user.availability
    presence = derive_effective_presence(get_or_create_presence(db, driver_user))
    if presence.effective_state == "available":
        from services.driver_status_service import sync_from_presence, touch_heartbeat

        sync_from_presence(
            db,
            driver_user,
            effective_state=presence.effective_state,
            lat=driver_user.last_latitude,
            lng=driver_user.last_longitude,
        )
        touch_heartbeat(db, driver_user)
    profile = (profile_availability or "").strip().lower()
    if profile not in _BLOCKED_PROFILE_AVAILABILITY and profile != DriverStatus.BUSY.value:
        driver_user.availability = "available" if presence.effective_state == "available" else "offline"
    ride_before_claim = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride_before_claim:
        record_ledger_entry(
            db,
            event_type="claim_attempted",
            ride_id=None,
            actor_id=driver_user.id,
            driver_id=driver_user.id,
            outcome="not_found",
            reason="ride_not_found",
            payload={"requested_ride_id": ride_id},
        )
        record_event(
            db,
            entity_type="claim",
            entity_id=ride_id,
            event_type="claim.attempted",
            actor_id=driver_user.id,
            payload={"outcome": "not_found", "reason": "ride_not_found"},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Ride not found")
    if (
        ride_before_claim.driver_id is not None
        or ride_before_claim.status == to_storage_ride_status(RideStatus.ACCEPTED)
    ):
        competing_driver_id = ride_before_claim.driver_id
        record_metric(db, "claim_conflict", 1.0, ride_id=ride_id, driver_id=driver_user.id)
        record_claim_attempt(
            db,
            ride_id=ride_id,
            driver_id=driver_user.id,
            outcome="conflict",
            competing_driver_id=competing_driver_id,
            reason="ride_already_claimed",
        )
        record_ledger_entry(
            db,
            event_type="claim_attempted",
            ride_id=ride_id,
            actor_id=driver_user.id,
            driver_id=driver_user.id,
            outcome="conflict",
            reason="ride_already_claimed",
            payload={"competing_driver_id": competing_driver_id},
        )
        record_ledger_entry(
            db,
            event_type="claim_lost",
            ride_id=ride_id,
            actor_id=driver_user.id,
            driver_id=driver_user.id,
            outcome="conflict",
            reason="ride_already_claimed",
            payload={"competing_driver_id": competing_driver_id},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=claim_conflict_detail(
                ride_id=ride_id,
                current_status=ride_before_claim.status,
                assigned_driver_id=competing_driver_id,
            ),
        )
    try:
        assert_driver_eligible_for_claim(
            db,
            driver=driver_user,
            effective_presence_state=presence.effective_state,
            profile_availability=profile_availability,
        )
    except DriverClaimIneligible as exc:
        if claim_block_uses_409(exc.reason):
            active_id = (
                driver_active_ride_id(db, driver_user.id)
                if exc.reason == "driver_already_on_active_ride"
                else None
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=driver_claim_blocked_detail(
                    ride_id=ride_id,
                    reason=exc.reason,
                    message=exc.message,
                    effective_presence_state=(
                        presence.effective_state if exc.reason.startswith("presence_") else None
                    ),
                    active_ride_id=active_id,
                ),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=auth_error_detail(exc.reason, exc.message),
        ) from exc
    if (
        ride_before_claim.driver_id is None
        and ride_before_claim.status != to_storage_ride_status(RideStatus.ACCEPTED)
    ):
        try:
            assert_driver_can_accept_ride(driver_user.availability, ride_before_claim.status)
        except (DriverUnavailableForRide, InvalidRideTransition) as exc:
            if isinstance(exc, DriverUnavailableForRide):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=auth_error_detail("forbidden", str(exc)),
                ) from exc
            _raise_invalid_transition(
                ride_id=ride_id,
                from_status=ride_before_claim.status,
                to_status=to_storage_ride_status(RideStatus.ACCEPTED),
                exc=exc,
            )
    if (
        sequential_dispatch_enabled()
        and ride_before_claim.driver_id is None
        and ride_before_claim.status == to_storage_ride_status(RideStatus.REQUESTED)
        and ride_before_claim.dispatch_driver_id is None
    ):
        start_dispatch_for_ride(db, ride_id)
        db.refresh(ride_before_claim)
    if (
        sequential_dispatch_enabled()
        and ride_before_claim.dispatch_driver_id is not None
        and ride_before_claim.dispatch_driver_id != driver_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=driver_claim_blocked_detail(
                ride_id=ride_id,
                reason="not_dispatch_candidate",
                message="No active dispatch offer for this driver on this ride",
            ),
        )
    try:
        ride = policy.claim_ride(db, ride_id, driver_user.id)
    except RideNotFound:
        record_ledger_entry(
            db,
            event_type="claim_attempted",
            ride_id=None,
            actor_id=driver_user.id,
            driver_id=driver_user.id,
            outcome="not_found",
            reason="ride_not_found",
            payload={"requested_ride_id": ride_id},
        )
        record_event(
            db,
            entity_type="claim",
            entity_id=ride_id,
            event_type="claim.attempted",
            actor_id=driver_user.id,
            payload={"outcome": "not_found", "reason": "ride_not_found"},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Ride not found")
    except RideAlreadyClaimed:
        claimed_ride = db.query(Ride).filter(Ride.id == ride_id).first()
        competing_driver_id = claimed_ride.driver_id if claimed_ride else None
        record_metric(db, "claim_conflict", 1.0, ride_id=ride_id, driver_id=driver_user.id)
        record_claim_attempt(
            db,
            ride_id=ride_id,
            driver_id=driver_user.id,
            outcome="conflict",
            competing_driver_id=competing_driver_id,
            reason="ride_already_claimed",
        )
        record_ledger_entry(
            db,
            event_type="claim_attempted",
            ride_id=ride_id,
            actor_id=driver_user.id,
            driver_id=driver_user.id,
            outcome="conflict",
            reason="ride_already_claimed",
            payload={"competing_driver_id": competing_driver_id},
        )
        record_ledger_entry(
            db,
            event_type="claim_lost",
            ride_id=ride_id,
            actor_id=driver_user.id,
            driver_id=driver_user.id,
            outcome="conflict",
            reason="ride_already_claimed",
            payload={"competing_driver_id": competing_driver_id},
        )
        record_event(
            db,
            entity_type="claim",
            entity_id=ride_id,
            event_type="claim.attempted",
            actor_id=driver_user.id,
            payload={"competing_driver_id": competing_driver_id, "reason": "ride_already_claimed"},
        )
        record_event(
            db,
            entity_type="claim",
            entity_id=ride_id,
            event_type="claim.lost",
            actor_id=driver_user.id,
            payload={"competing_driver_id": competing_driver_id, "reason": "ride_already_claimed"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=claim_conflict_detail(
                ride_id=ride_id,
                current_status=claimed_ride.status if claimed_ride else None,
                assigned_driver_id=competing_driver_id,
            ),
        )
    except RideNotAvailable:
        record_claim_attempt(
            db,
            ride_id=ride_id,
            driver_id=driver_user.id,
            outcome="unavailable",
            reason="ride_not_available",
        )
        record_ledger_entry(
            db,
            event_type="claim_attempted",
            ride_id=ride_id,
            actor_id=driver_user.id,
            driver_id=driver_user.id,
            outcome="unavailable",
            reason="ride_not_available",
        )
        record_ledger_entry(
            db,
            event_type="claim_lost",
            ride_id=ride_id,
            actor_id=driver_user.id,
            driver_id=driver_user.id,
            outcome="unavailable",
            reason="ride_not_available",
        )
        record_event(
            db,
            entity_type="claim",
            entity_id=ride_id,
            event_type="claim.attempted",
            actor_id=driver_user.id,
            payload={"outcome": "unavailable", "reason": "ride_not_available"},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ride not available")
    record_claim_attempt(db, ride_id=ride_id, driver_id=driver_user.id, outcome="won")
    record_ledger_entry(
        db,
        event_type="claim_attempted",
        ride_id=ride_id,
        actor_id=driver_user.id,
        driver_id=driver_user.id,
        outcome="won",
    )
    record_ledger_entry(
        db,
        event_type="claim_won",
        ride_id=ride_id,
        actor_id=driver_user.id,
        driver_id=driver_user.id,
        outcome="won",
    )
    record_accept_metrics(db, ride=ride, driver_id=driver_user.id)
    record_event(
        db,
        entity_type="claim",
        entity_id=ride_id,
        event_type="claim.attempted",
        actor_id=driver_user.id,
        payload={"outcome": "won"},
    )
    record_event(
        db,
        entity_type="claim",
        entity_id=ride_id,
        event_type="claim.won",
        actor_id=driver_user.id,
        payload={"outcome": "won"},
    )
    from services.ride_lifecycle_events import record_ride_lifecycle_event

    record_ride_lifecycle_event(
        db,
        ride_id=ride_id,
        event_type="ride.accepted",
        from_state=RideStatus.REQUESTED,
        to_state=RideStatus.ACCEPTED,
        reason="driver_action",
        actor="driver",
        actor_id=driver_user.id,
    )
    record_dispatch_accepted(db, ride, driver_user.id)
    ground_ride_route(ride)
    db.commit()
    db.refresh(ride)
    notify_driver_in_app(
        db,
        driver_id=driver_user.id,
        title="Ride accepted",
        message=f"You accepted ride #{ride_id}. Head to pickup when ready.",
        notif_type=NotificationType.RIDE_ACCEPTED,
    )
    from services.ride_payment import authorize_payment_for_ride

    authorize_payment_for_ride(db, ride)
    db.commit()
    _broadcast_pool_ride_removed(ride_id=ride_id, event=POOL_EVENT_CLAIMED)
    return RideTransitionResponse(
        message=f"Ride {ride_id} accepted successfully",
        ride=ride_to_view(ride, db=db),
    )


@router.post("/decline-ride/{ride_id}", response_model=RideTransitionResponse)
def decline_ride(
    ride_id: int,
    request: Request,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    body: Union[DeclineRideBody, None] = Body(default=None),
):
    driver_user = load_principal_user(db, driver_user)
    return execute_idempotent_ride_write(
        request,
        db,
        driver_user.id,
        "drivers.decline-ride",
        "decline",
        ride_id,
        lambda: _decline_ride_impl(ride_id, driver_user, db, body),
        RideTransitionResponse,
    )


def _decline_ride_impl(
    ride_id: int,
    driver_user,
    db: Session,
    body: Union[DeclineRideBody, None],
):
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    from_status = normalize_ride_status(ride.status).value
    try:
        next_status = release_accepted_ride_to_pool(ride.status, UserRole.DRIVER)
    except InvalidRideTransition as exc:
        _raise_invalid_transition(
            ride_id=ride_id,
            from_status=from_status,
            to_status=to_storage_ride_status(RideStatus.REQUESTED),
            exc=exc,
        )
    if ride.driver_id != driver_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=invalid_state_transition_detail(
                ride_id=ride_id,
                from_status=from_status,
                to_status=to_storage_ride_status(RideStatus.REQUESTED),
                message="Ride cannot be declined in its current state",
            ),
        )

    try:
        assert_driver_can_perform_ride_action(
            db, driver=driver_user, ride_id=ride_id, action="decline"
        )
    except DriverApprovalDenied as exc:
        _raise_approval_denied(exc)

    reason = (body.reason.strip() if body and body.reason else None) if body else None
    ride.status = to_storage_ride_status(next_status)
    ride.driver_id = None
    _clear_active_leg(ride)
    ride.lifecycle_reason = reason
    record_event(
        db,
        entity_type="ride",
        entity_id=ride_id,
        event_type="ride.declined",
        actor_id=driver_user.id,
        payload={"reason": reason},
    )
    record_ledger_entry(
        db,
        event_type="claim_released",
        ride_id=ride_id,
        actor_id=driver_user.id,
        driver_id=driver_user.id,
        outcome="released",
        reason=reason,
    )
    notify_driver_in_app(
        db,
        driver_id=driver_user.id,
        title="Ride released",
        message=f"Ride #{ride_id} was returned to the open board.",
        notif_type=NotificationType.RIDE_CANCELLED,
    )
    db.commit()
    db.refresh(ride)
    return RideTransitionResponse(
        message=f"Ride {ride_id} returned to the pool",
        ride=ride_to_view(ride, db=db),
    )


@router.post("/decline-dispatch/{ride_id}", response_model=RideTransitionResponse)
def decline_dispatch_offer(
    ride_id: int,
    request: Request,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """Decline the current sequential dispatch offer (RIDE-003); ride stays unassigned."""
    driver_user = load_principal_user(db, driver_user)
    return execute_idempotent_ride_write(
        request,
        db,
        driver_user.id,
        "drivers.decline-dispatch",
        "decline_dispatch",
        ride_id,
        lambda: _decline_dispatch_offer_impl(ride_id, driver_user, db),
        RideTransitionResponse,
    )


def _decline_dispatch_offer_impl(ride_id: int, driver_user, db: Session):
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    from models.ride_dispatch_log import DISPATCH_RESULT_PENDING, RideDispatchLog

    pending_offer = (
        db.query(RideDispatchLog)
        .filter(
            RideDispatchLog.ride_id == ride_id,
            RideDispatchLog.driver_id == driver_user.id,
            RideDispatchLog.result == DISPATCH_RESULT_PENDING,
        )
        .first()
    )
    if ride.dispatch_driver_id != driver_user.id and pending_offer is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No active dispatch offer for this driver on this ride",
        )
    record_dispatch_declined(db, ride_id, driver_user.id)
    record_event(
        db,
        entity_type="ride",
        entity_id=ride_id,
        event_type="ride.dispatch_declined",
        actor_id=driver_user.id,
        payload={"attempt": ride.dispatch_attempt_count},
    )
    db.commit()
    db.refresh(ride)
    return RideTransitionResponse(
        message=f"Dispatch offer declined for ride {ride_id}",
        ride=ride_to_view(ride, db=db),
    )


@router.post("/dismiss-ride/{ride_id}", response_model=RideTransitionResponse)
def dismiss_ride(
    ride_id: int,
    request: Request,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    return hide_ride(
        ride_id,
        request,
        HideRideBody(reason="legacy_dismiss_endpoint"),
        driver_user,
        db,
    )


@router.post("/rides/{ride_id}/hide", response_model=RideTransitionResponse)
def hide_ride(
    ride_id: int,
    request: Request,
    body: Union[HideRideBody, None] = Body(default=None),
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    return execute_idempotent_ride_write(
        request,
        db,
        driver_user.id,
        "drivers.rides.hide",
        "hide",
        ride_id,
        lambda: _hide_ride_impl(ride_id, body, driver_user, db),
        RideTransitionResponse,
    )


def _hide_ride_impl(
    ride_id: int,
    body: Union[HideRideBody, None],
    driver_user,
    db: Session,
):
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.status != to_storage_ride_status(RideStatus.REQUESTED) or ride.driver_id is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ride cannot be hidden in its current state")

    reason = (body.reason.strip() if body and body.reason else None) if body else None
    visibility = dismiss_visible_ride(db, ride_id=ride_id, driver_id=driver_user.id, reason=reason)
    record_event(
        db,
        entity_type="ride",
        entity_id=ride_id,
        event_type="ride.hidden",
        actor_id=driver_user.id,
        payload={
            "status": ride.status,
            "reason": reason,
            "visibility_record_id": visibility.id,
            "visibility_correlation_id": visibility.correlation_id,
            "expires_at": _iso(visibility.expires_at),
            "ttl_seconds": RIDE_HIDE_TTL_SECONDS,
        },
    )
    db.commit()
    return RideTransitionResponse(
        message=f"Ride {ride_id} hidden for driver {driver_user.id}",
        ride=ride_to_view(ride, db=db),
    )


def _raise_approval_denied(exc: DriverApprovalDenied) -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=auth_error_detail(exc.error_code, exc.message),
    ) from exc


@router.post("/arrive-pickup/{ride_id}", response_model=RideTransitionResponse)
def arrive_pickup(
    ride_id: int,
    request: Request,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    return execute_idempotent_ride_write(
        request,
        db,
        driver_user.id,
        "drivers.arrive-pickup",
        "arrive",
        ride_id,
        lambda: _arrive_pickup_impl(ride_id, driver_user, db),
        RideTransitionResponse,
    )


def _arrive_pickup_impl(ride_id: int, driver_user, db: Session):
    try:
        assert_driver_can_perform_ride_action(db, driver=driver_user, ride_id=ride_id, action="arrive")
    except DriverApprovalDenied as exc:
        _raise_approval_denied(exc)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id != driver_user.id:
        try:
            next_ride_status(ride.status, RideAction.ARRIVE, UserRole.DRIVER)
        except InvalidRideTransition as exc:
            _raise_invalid_transition(
                ride_id=ride_id,
                from_status=normalize_ride_status(ride.status).value,
                to_status=target_status_for_action(RideAction.ARRIVE.value),
                exc=exc,
            )
        raise HTTPException(status_code=404, detail="Ride not found or not assigned to you")
    from_status = normalize_ride_status(ride.status)
    try:
        ride.status = to_storage_ride_status(next_ride_status(ride.status, RideAction.ARRIVE, UserRole.DRIVER))
    except InvalidRideTransition as exc:
        _raise_invalid_transition(
            ride_id=ride_id,
            from_status=from_status.value,
            to_status=target_status_for_action(RideAction.ARRIVE.value),
            exc=exc,
        )

    ride.arrived_pickup_at = utc_now_naive()
    record_started_metrics(db, ride=ride, driver_id=driver_user.id)
    from services.ride_lifecycle_events import record_ride_lifecycle_event

    record_ride_lifecycle_event(
        db,
        ride_id=ride_id,
        event_type="ride.arrived_pickup",
        from_state=from_status,
        to_state=RideStatus.DRIVER_ARRIVED,
        reason="driver_action",
        actor="driver",
        actor_id=driver_user.id,
    )
    notify_driver_in_app(
        db,
        driver_id=driver_user.id,
        title="Arrived at pickup",
        message=f"You marked arrival for ride #{ride_id}.",
        notif_type=NotificationType.SYSTEM,
    )
    db.commit()
    db.refresh(ride)
    return RideTransitionResponse(
        message=f"Arrival recorded for ride {ride_id}",
        ride=ride_to_view(ride, db=db),
    )


@router.post("/start-ride/{ride_id}", response_model=RideTransitionResponse)
def start_ride(
    ride_id: int,
    request: Request,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    return execute_idempotent_ride_write(
        request,
        db,
        driver_user.id,
        "drivers.start-ride",
        "start",
        ride_id,
        lambda: _start_ride_impl(ride_id, driver_user, db),
        RideTransitionResponse,
    )


def _start_ride_impl(ride_id: int, driver_user, db: Session):
    try:
        assert_driver_can_perform_ride_action(db, driver=driver_user, ride_id=ride_id, action="start")
    except DriverApprovalDenied as exc:
        _raise_approval_denied(exc)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id != driver_user.id:
        try:
            next_ride_status(ride.status, RideAction.START, UserRole.DRIVER)
        except InvalidRideTransition as exc:
            _raise_invalid_transition(
                ride_id=ride_id,
                from_status=normalize_ride_status(ride.status).value,
                to_status=target_status_for_action(RideAction.START.value),
                exc=exc,
            )
        raise HTTPException(status_code=404, detail="Ride not found or not assigned to you")
    from_status = normalize_ride_status(ride.status)
    try:
        ride.status = to_storage_ride_status(next_ride_status(ride.status, RideAction.START, UserRole.DRIVER))
    except InvalidRideTransition as exc:
        _raise_invalid_transition(
            ride_id=ride_id,
            from_status=from_status.value,
            to_status=target_status_for_action(RideAction.START.value),
            exc=exc,
        )

    ride.started_at = utc_now_naive()
    record_started_metrics(db, ride=ride, driver_id=driver_user.id)
    from services.ride_lifecycle_events import record_ride_lifecycle_event

    record_ride_lifecycle_event(
        db,
        ride_id=ride_id,
        event_type="ride.started",
        from_state=from_status,
        to_state=RideStatus.IN_PROGRESS,
        reason="driver_action",
        actor="driver",
        actor_id=driver_user.id,
    )
    notify_driver_in_app(
        db,
        driver_id=driver_user.id,
        title="Ride started",
        message=f"Ride #{ride_id} is in progress.",
        notif_type=NotificationType.SYSTEM,
    )
    db.commit()
    db.refresh(ride)
    return RideTransitionResponse(
        message=f"Ride {ride_id} in progress",
        ride=ride_to_view(ride, db=db),
    )


@router.post("/complete-ride/{ride_id}", response_model=CompleteRideResponse)
def complete_ride(
    ride_id: int,
    request: Request,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    body: Union[CompleteRidePricingBody, None] = Body(default=None),
):
    driver_user = load_principal_user(db, driver_user)
    return execute_idempotent_ride_write(
        request,
        db,
        driver_user.id,
        "drivers.complete-ride",
        "complete",
        ride_id,
        lambda: _complete_ride_impl(ride_id, driver_user, db, body),
        CompleteRideResponse,
    )


def _complete_ride_impl(
    ride_id: int,
    driver_user,
    db: Session,
    body: Union[CompleteRidePricingBody, None],
):
    try:
        assert_driver_can_perform_ride_action(db, driver=driver_user, ride_id=ride_id, action="complete")
    except DriverApprovalDenied as exc:
        _raise_approval_denied(exc)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id != driver_user.id:
        try:
            next_ride_status(ride.status, RideAction.COMPLETE, UserRole.DRIVER)
        except InvalidRideTransition as exc:
            _raise_invalid_transition(
                ride_id=ride_id,
                from_status=normalize_ride_status(ride.status).value,
                to_status=target_status_for_action(RideAction.COMPLETE.value),
                exc=exc,
            )
        raise HTTPException(status_code=404, detail="Ride not found or not assigned to you")
    existing_pricing = get_ride_pricing(db, ride_id)
    if existing_pricing and existing_pricing.financial_locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ride financial fields are locked after completion",
        )
    from_status = normalize_ride_status(ride.status)
    try:
        ride.status = to_storage_ride_status(next_ride_status(ride.status, RideAction.COMPLETE, UserRole.DRIVER))
    except InvalidRideTransition as exc:
        _raise_invalid_transition(
            ride_id=ride_id,
            from_status=from_status.value,
            to_status=target_status_for_action(RideAction.COMPLETE.value),
            exc=exc,
        )

    ride.completed_at = utc_now_naive()
    dist = ride.distance or 0.0
    pricing_body = body or CompleteRidePricingBody()
    try:
        pricing_row = finalize_ride_pricing(
            db,
            ride_id=ride_id,
            distance_km=dist,
            duration_minutes=ride.duration or 0,
            platform_service_fee_cents=pricing_body.platform_service_fee_cents,
            tip_cents=pricing_body.tip_cents,
            city_fee_cents=pricing_body.city_fee_cents,
            airport_fee_cents=pricing_body.airport_fee_cents,
            toll_cents=pricing_body.toll_cents,
            accessibility_fee_cents=pricing_body.accessibility_fee_cents,
            tax_cents=pricing_body.tax_cents,
            lock=True,
        )
    except PricingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    ride.fare_amount = cents_to_display_dollars(pricing_row.driver_earnings_cents)
    stamp_route_calculated(ride)
    create_route_snapshot(
        db,
        ride=ride,
        route_result=None,
        snapshot_role=SNAPSHOT_ROLE_COMPLETE,
        pricing=pricing_row,
        provenance={"source": "driver_complete", "financial_locked": True},
    )
    generate_settlement_entries(db, ride_id=ride_id)
    try:
        execution = create_charge_intent_from_pricing(db, ride.id)
        try_start_stripe_charge_for_ride(db, execution, ride.driver_id)
    except (ValueError, Exception):
        # Execution is async/replayable; ride completion must not depend on PSP.
        pass
    record_completed_metrics(db, ride=ride, driver_id=driver_user.id)
    from services.ride_lifecycle_events import record_ride_lifecycle_event

    record_ride_lifecycle_event(
        db,
        ride_id=ride_id,
        event_type="ride.completed",
        from_state=from_status,
        to_state=RideStatus.COMPLETED,
        reason="driver_action",
        actor="driver",
        actor_id=driver_user.id,
        extra={
            "fare_amount": ride.fare_amount,
            "distance_km": dist,
            "driver_earnings_cents": pricing_row.driver_earnings_cents,
            "platform_earnings_cents": pricing_row.platform_earnings_cents,
        },
    )
    record_event(
        db,
        entity_type="earning",
        entity_id=ride_id,
        event_type="earning.calculated",
        actor_id=driver_user.id,
        payload={
            "driver_earnings_cents": pricing_row.driver_earnings_cents,
            "platform_earnings_cents": pricing_row.platform_earnings_cents,
            "driver_shareable_fare_cents": pricing_row.driver_shareable_fare_cents,
        },
    )
    from services.ride_payment import capture_payment_for_ride

    capture_payment_for_ride(db, ride)

    db.commit()
    db.refresh(ride)
    notify_driver_in_app(
        db,
        driver_id=driver_user.id,
        title="Ride completed",
        message=f"Ride #{ride_id} completed. Earnings are recorded in your ledger.",
        notif_type=NotificationType.RIDE_COMPLETED,
    )
    db.commit()
    return CompleteRideResponse(
        message=f"Ride {ride_id} completed successfully",
        fare_earned=ride.fare_amount or 0.0,
        ride=ride_to_view(ride, db=db),
    )


@router.get("/rides/{ride_id}/payment", response_model=RidePaymentResponse)
def get_ride_payment_for_driver(
    ride_id: int,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride or ride.driver_id != driver_user.id:
        raise HTTPException(status_code=404, detail="Ride not found")
    from services.ride_payment import get_ride_payment, payment_to_dict

    payment = get_ride_payment(db, ride_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {
        "message": f"Payment for ride {ride_id}",
        "payment": RidePaymentView.model_validate(payment_to_dict(payment)),
    }


@router.get("/me/ride-payments", response_model=DriverRidePaymentsResponse)
def list_my_ride_payments(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    from models.payment import PAYMENT_STATUS_CAPTURED, RidePayment
    from services.ride_payment import payment_to_dict

    rows = (
        db.query(RidePayment)
        .filter(RidePayment.driver_id == driver_user.id)
        .order_by(RidePayment.id.desc())
        .limit(100)
        .all()
    )
    payments = [RidePaymentView.model_validate(payment_to_dict(row)) for row in rows]
    total = sum(p.amount_cents for p in rows if p.status == PAYMENT_STATUS_CAPTURED)
    return {
        "message": "Driver ride payments",
        "payments": payments,
        "total_captured_cents": total,
    }


@router.get("/earnings", response_model=DriverEarningsResponse)
def get_driver_earnings(driver_user: AuthPrincipal = Depends(DRIVER_ACCESS), db: Session = Depends(get_db)):
    driver_user = load_principal_user(db, driver_user)
    completed_rides = (
        db.query(Ride)
        .filter(
            Ride.driver_id == driver_user.id,
            Ride.status == to_storage_ride_status(RideStatus.COMPLETED),
        )
        .all()
    )

    def _driver_earnings_dollars(ride: Ride) -> float:
        row = get_ride_pricing(db, ride.id)
        if row and row.financial_locked:
            return cents_to_display_dollars(row.driver_earnings_cents)
        return float(ride.fare_amount or 0)

    total_earnings = sum(_driver_earnings_dollars(ride) for ride in completed_rides)
    total_rides = len(completed_rides)

    week_start = utc_now_naive() - timedelta(days=7)
    weekly_rides = [ride for ride in completed_rides if ride.completed_at and ride.completed_at >= week_start]
    weekly_earnings = sum(_driver_earnings_dollars(ride) for ride in weekly_rides)

    today_start = utc_now_naive().replace(hour=0, minute=0, second=0, microsecond=0)
    today_rides = [ride for ride in completed_rides if ride.completed_at and ride.completed_at >= today_start]
    today_earnings = sum(_driver_earnings_dollars(ride) for ride in today_rides)

    summary = EarningsSummary(
        total_earnings=round(total_earnings, 2),
        weekly_earnings=round(weekly_earnings, 2),
        today_earnings=round(today_earnings, 2),
        total_rides_completed=total_rides,
        weekly_rides=len(weekly_rides),
        today_rides=len(today_rides),
    )
    recent = [
        EarningsRecentRide(
            id=ride.id,
            customer_name=ride.customer_name,
            fare_amount=_driver_earnings_dollars(ride),
            distance_km=ride.distance,
            completed_at=_iso(ride.completed_at),
            rating=ride.rating,
        )
        for ride in completed_rides[-10:]
    ]
    return DriverEarningsResponse(
        driver_id=driver_user.id,
        driver_name=driver_user.name,
        earnings_summary=summary,
        recent_rides=recent,
    )


@router.get("/me/payment-reconciliation")
def get_my_payment_reconciliation(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """
  Pricing vs PSP execution reconciliation for this driver.
  Does not claim bank payout or instant deposit — execution layer only.
    """
    driver_user = load_principal_user(db, driver_user)
    base = compute_driver_payment_reconciliation(db, driver_user.id)
    return enrich_reconciliation_with_payouts(db, driver_user.id, base)


@router.get("/me/payment-executions")
def get_my_payment_executions(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """Recent payment_execution rows for this driver's rides (PSP layer only)."""
    driver_user = load_principal_user(db, driver_user)
    items = list_driver_payment_executions(db, driver_user.id)
    return {"items": items}


@router.get("/me/payouts")
def get_my_payouts(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """
    Provider-reported Connect payouts for this driver (read-only).
    Status comes from Stripe payout objects — not bank deposit confirmation.
    """
    driver_user = load_principal_user(db, driver_user)
    items = list_driver_payouts(db, driver_user.id)
    return {"items": items}


@router.get("/performance")
def get_driver_performance(driver_user: AuthPrincipal = Depends(DRIVER_ACCESS), db: Session = Depends(get_db)):
    driver_user = load_principal_user(db, driver_user)
    return get_driver_performance_snapshot(db, driver_id=driver_user.id)


@router.get("/insights")
def get_measured_driver_insights(driver_user: AuthPrincipal = Depends(DRIVER_ACCESS), db: Session = Depends(get_db)):
    driver_user = load_principal_user(db, driver_user)
    return get_driver_insights(db, driver_id=driver_user.id)


@router.get("/profile")
def get_driver_profile(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """
    Read-only driver profile/settings projection.
    Does not update anything.
    Does not collect onboarding/payment/dossier data.
    """
    driver_user = load_principal_user(db, driver_user)
    approval = get_driver_approval(db, driver_user.id)
    approval_status = approval_status_value(approval)
    role_value = (
        getattr(getattr(driver_user, "role", None), "value", None) or getattr(driver_user, "role", None)
    )

    def _vehicle_field(value: Optional[str]) -> str:
        return value if value else "Not registered"

    return {
        "id": driver_user.id,
        "email": driver_user.email,
        "name": driver_user.name,
        "role": role_value,
        "license_no": driver_user.license_no,
        "approval_status": approval_status,
        "vehicle": {
            "make": _vehicle_field(driver_user.vehicle_make),
            "model": _vehicle_field(driver_user.vehicle_model),
            "plate": _vehicle_field(driver_user.license_plate),
        },
        "vehicle_year": driver_user.vehicle_year,
        "vehicle_ready": bool(driver_user.vehicle_ready),
        "insurance_policy": driver_user.insurance_policy,
        "insurance_expires_at": (
            driver_user.insurance_expires_at.isoformat()
            if driver_user.insurance_expires_at
            else None
        ),
        "read_only": True,
    }


@router.put("/profile")
def update_driver_profile(
    body: DriverProfileUpdate,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    if body.name is not None:
        new_name = body.name.strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        driver_user.name = new_name
    if body.phone is not None:
        driver_user.phone = body.phone.strip() or None
    if body.emergency_contact is not None:
        driver_user.emergency_contact = body.emergency_contact.strip() or None
    if body.vehicle_make is not None:
        driver_user.vehicle_make = body.vehicle_make.strip() or None
    if body.vehicle_model is not None:
        driver_user.vehicle_model = body.vehicle_model.strip() or None
    if body.vehicle_year is not None:
        if body.vehicle_year < 1900 or body.vehicle_year > 2100:
            raise HTTPException(status_code=400, detail="vehicle_year out of allowed range")
        driver_user.vehicle_year = body.vehicle_year
    if body.license_plate is not None:
        driver_user.license_plate = body.license_plate.strip() or None
    if body.insurance_policy is not None:
        driver_user.insurance_policy = body.insurance_policy.strip() or None
    if body.availability is not None:
        driver_user.availability = body.availability

    db.commit()
    db.refresh(driver_user)
    return {
        "message": "Profile updated",
        "profile": {
            "id": driver_user.id,
            "email": driver_user.email,
            "name": driver_user.name,
            "role": driver_user.role.value,
            "license_no": driver_user.license_no,
            "phone": driver_user.phone,
            "emergency_contact": driver_user.emergency_contact,
            "vehicle_make": driver_user.vehicle_make,
            "vehicle_model": driver_user.vehicle_model,
            "vehicle_year": driver_user.vehicle_year,
            "license_plate": driver_user.license_plate,
            "insurance_policy": driver_user.insurance_policy,
            "insurance_expires_at": (
                driver_user.insurance_expires_at.isoformat()
                if driver_user.insurance_expires_at
                else None
            ),
            "vehicle_ready": bool(driver_user.vehicle_ready),
            "availability": driver_user.availability,
            "last_latitude": driver_user.last_latitude,
            "last_longitude": driver_user.last_longitude,
            "last_location_at": driver_user.last_location_at,
        },
    }


@router.get("/me/profile", response_model=DriverMeProfileOut)
def get_my_driver_profile(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """App profile overlay (display name, phone, photo) — separate from GET /drivers/profile."""
    driver_user = load_principal_user(db, driver_user)
    row = get_or_create_profile(db, driver_user.id)
    db.commit()
    return DriverMeProfileOut(**profile_to_dict(row))


@router.put("/me/profile", response_model=DriverMeProfileOut)
def put_my_driver_profile(
    body: DriverMeProfileIn,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    row = update_profile(db, driver_user.id, body.model_dump(exclude_unset=True))
    db.commit()
    return DriverMeProfileOut(**profile_to_dict(row))


@router.get("/me/settings", response_model=DriverAppSettingsOut)
def get_my_driver_app_settings(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    """Driver app preferences (units, theme, notification toggles). Push delivery is Slice 04+."""
    driver_user = load_principal_user(db, driver_user)
    row = get_or_create_settings(db, driver_user.id)
    db.commit()
    return DriverAppSettingsOut(**settings_to_dict(row))


@router.put("/me/settings", response_model=DriverAppSettingsOut)
def put_my_driver_app_settings(
    body: DriverAppSettingsIn,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    try:
        row = update_settings(db, driver_user.id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return DriverAppSettingsOut(**settings_to_dict(row))


@router.get("/status", response_model=DriverStatusResponse)
def get_driver_status(driver_user: AuthPrincipal = Depends(DRIVER_ACCESS), db: Session = Depends(get_db)):
    driver_user = load_principal_user(db, driver_user)
    return {
        "driver_id": driver_user.id,
        "status": driver_user.availability,
        "updated_at": driver_user.last_location_at,
    }


@router.post("/update-location", response_model=DriverLocationUpdateResponse)
def update_driver_location(
    body: LocationUpdate,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    driver_user = load_principal_user(db, driver_user)
    driver_user.last_latitude = body.latitude
    driver_user.last_longitude = body.longitude
    driver_user.last_location_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "message": "Location updated",
        "driver_id": driver_user.id,
        "status": driver_user.availability,
        "latitude": driver_user.last_latitude,
        "longitude": driver_user.last_longitude,
        "updated_at": driver_user.last_location_at,
    }


@router.get("/statistics")
def get_driver_statistics(driver_user: AuthPrincipal = Depends(DRIVER_ACCESS), db: Session = Depends(get_db)):
    driver_user = load_principal_user(db, driver_user)
    all_rides = db.query(Ride).filter(Ride.driver_id == driver_user.id).all()
    completed_rides = [ride for ride in all_rides if ride.status == to_storage_ride_status(RideStatus.COMPLETED)]

    total_distance = sum(ride.distance or 0 for ride in completed_rides)
    total_duration = sum(ride.duration or 0 for ride in completed_rides)
    rated = [ride for ride in completed_rides if ride.rating]
    average_rating = sum(ride.rating or 0 for ride in rated) / len(rated) if rated else 0

    accepted_or_beyond = [r for r in all_rides if r.status in _STATUSES_PAST_POOL]

    return {
        "driver_id": driver_user.id,
        "driver_name": driver_user.name,
        "performance_stats": {
            "total_rides_requested": len([r for r in all_rides if r.status == to_storage_ride_status(RideStatus.REQUESTED)]),
            "total_rides_accepted": len(accepted_or_beyond),
            "total_rides_completed": len(completed_rides),
            "completion_rate": round(len(completed_rides) / len(all_rides) * 100, 2) if all_rides else 0,
            "total_distance_km": round(total_distance, 2),
            "total_hours_driven": round(total_duration / 60, 2),
            "average_rating": round(average_rating, 2),
            "earnings_per_ride": round(
                sum(ride.fare_amount or 0 for ride in completed_rides) / len(completed_rides), 2
            )
            if completed_rides
            else 0,
        },
    }
