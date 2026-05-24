import json
from datetime import datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from typing import Iterable
from uuid import uuid4

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from models.ledger import MarketplaceLedgerEntry, MarketplaceLedgerEvent
from models.metrics import Event, Metric, RideClaimAttempt, RideVisibility
from models.ride import Ride
from models.user import User, UserRole
from services.datetime_utils import utc_now_naive
from services.lifecycle import DriverStatus, RideStatus, to_storage_ride_status

DISPATCH_POLICY_VERSION = "ranked_open_board_v1"
DISPATCH_POLICY_NAME = "Ranked Open Board v1"
DISPATCH_ORDERING_RULE = ("ordering_score_desc", "created_at_asc", "ride_id_asc")
DISPATCH_VISIBILITY_REASON = "requested_unassigned_open_board"
RIDE_HIDE_TTL_SECONDS = 15 * 60
SLOW_MATCH_SECONDS = 5 * 60
ABANDONED_REQUEST_SECONDS = 15 * 60
EXCESSIVE_COMPETITION_ATTEMPTS = 3


def _seconds_between(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return max((end - start).total_seconds(), 0.0)


def record_metric(
    db: Session,
    name: str,
    value: float,
    *,
    ride_id: int | None = None,
    driver_id: int | None = None,
) -> Metric:
    metric = Metric(metric_name=name, value=value, ride_id=ride_id, driver_id=driver_id)
    db.add(metric)
    return metric


def _haversine_km(lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None) -> float | None:
    if any(value is None for value in (lat1, lon1, lat2, lon2)):
        return None
    lat1_f, lon1_f, lat2_f, lon2_f = (float(value) for value in (lat1, lon1, lat2, lon2))
    radius_km = 6371.0
    d_lat = radians(lat2_f - lat1_f)
    d_lon = radians(lon2_f - lon1_f)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1_f)) * cos(radians(lat2_f)) * sin(d_lon / 2) ** 2
    )
    return radius_km * 2 * atan2(sqrt(a), sqrt(1 - a))


def rank_available_rides(db: Session, *, driver: User, rides: Iterable[Ride]) -> list[Ride]:
    now = utc_now_naive()
    ranked: list[tuple[Ride, float, dict]] = []
    for ride in rides:
        distance_km = _haversine_km(
            driver.last_latitude,
            driver.last_longitude,
            ride.pickup_latitude,
            ride.pickup_longitude,
        )
        age_seconds = _seconds_between(ride.created_at, now) or 0.0
        distance_points = max(0.0, 100.0 - (distance_km * 10.0)) if distance_km is not None else 0.0
        age_points = min(age_seconds / 60.0, 120.0)
        score = round(distance_points + age_points, 4)
        why_this_rank = {
            "distance_factor": (
                f"{distance_km:.2f} km from last stored driver location"
                if distance_km is not None
                else "unavailable: driver or pickup coordinates missing"
            ),
            "fairness_factor": "not used: no fairness rotation counter is stored yet",
            "availability_factor": "available open-board ride; older requested rides receive higher age points",
            "age_seconds": round(age_seconds, 3),
        }
        ranked.append((ride, score, why_this_rank))

    ranked.sort(key=lambda item: (-item[1], item[0].created_at, item[0].id))
    for rank, (ride, score, why_this_rank) in enumerate(ranked, start=1):
        ride.ordering_rank = rank
        ride.ordering_score = score
        ride.why_this_rank = why_this_rank
        ride.dispatch_policy_id = DISPATCH_POLICY_VERSION
        ride.dispatch_policy_name = DISPATCH_POLICY_NAME
    return [ride for ride, _, _ in ranked]


def record_available_rides(
    db: Session,
    *,
    driver_id: int,
    rides: Iterable[Ride],
    policy_version: str = DISPATCH_POLICY_VERSION,
) -> dict[int, dict]:
    now = utc_now_naive()
    visible_rides = list(rides)
    record_metric(db, "rides_visible_count", float(len(visible_rides)), driver_id=driver_id)
    metadata_by_ride_id: dict[int, dict] = {}

    for rank, ride in enumerate(visible_rides, start=1):
        why_this_rank = getattr(ride, "why_this_rank", None) or {}
        visibility = (
            db.query(RideVisibility)
            .filter(
                RideVisibility.ride_id == ride.id,
                RideVisibility.driver_id == driver_id,
                RideVisibility.policy_version == policy_version,
            )
            .first()
        )
        metadata_payload = {
            "source": "GET /drivers/available-rides",
            "dispatch_policy_id": policy_version,
            "dispatch_policy_name": getattr(ride, "dispatch_policy_name", DISPATCH_POLICY_NAME),
            "ordered_by": list(DISPATCH_ORDERING_RULE),
            "visibility_reason": DISPATCH_VISIBILITY_REASON,
        }
        metadata = json.dumps(metadata_payload, sort_keys=True)
        emit_visible_event = False
        if visibility:
            emit_visible_event = visibility.status != "visible"
            visibility.dismissed_at = None
            visibility.expires_at = None
            visibility.reason = None
            visibility.last_seen_at = now
            visibility.status = "visible"
            visibility.ordering_rank = rank
            visibility.ordering_score = getattr(ride, "ordering_score", None)
            visibility.why_this_rank_json = json.dumps(why_this_rank, sort_keys=True)
            visibility.metadata_json = metadata
            visibility.correlation_id = visibility.correlation_id or uuid4().hex
        else:
            visibility = RideVisibility(
                ride_id=ride.id,
                driver_id=driver_id,
                first_seen_at=now,
                last_seen_at=now,
                status="visible",
                policy_version=policy_version,
                ordering_rank=rank,
                ordering_score=getattr(ride, "ordering_score", None),
                why_this_rank_json=json.dumps(why_this_rank, sort_keys=True),
                metadata_json=metadata,
                correlation_id=uuid4().hex,
            )
            db.add(visibility)
            record_metric(db, "rides_seen_before_accept", 1.0, ride_id=ride.id, driver_id=driver_id)
            emit_visible_event = True
        db.flush()
        if emit_visible_event:
            from services.ledger import MarketplaceLedgerEventType, append_marketplace_event

            append_marketplace_event(
                db,
                event_type=MarketplaceLedgerEventType.DISPATCH_RIDE_VISIBLE,
                entity_type="ride_visibility",
                entity_id=visibility.id,
                ride_id=ride.id,
                driver_id=driver_id,
                correlation_id=visibility.correlation_id,
                idempotency_key=f"ride-visible:{visibility.id}:{now.isoformat()}",
                payload={
                    "dispatch_policy_id": policy_version,
                    "dispatch_policy_name": metadata_payload["dispatch_policy_name"],
                    "ordered_by": metadata_payload["ordered_by"],
                    "ordering_rank": rank,
                    "ordering_score": getattr(ride, "ordering_score", None),
                    "visibility_reason": metadata_payload["visibility_reason"],
                    "why_this_rank": why_this_rank,
                },
                policy_version=policy_version,
            )
        metadata_by_ride_id[ride.id] = {
            "ride_visibility_id": visibility.id,
            "visibility_correlation_id": visibility.correlation_id,
            "visibility_reason": metadata_payload["visibility_reason"],
            "ordering_rank": rank,
            "ordering_score": getattr(ride, "ordering_score", None),
            "why_this_rank": why_this_rank,
            "dispatch_policy_id": policy_version,
            "dispatch_policy_name": metadata_payload["dispatch_policy_name"],
            "ordered_by": metadata_payload["ordered_by"],
            "policy_version": policy_version,
            "generated_at": now,
        }

    db.commit()
    return metadata_by_ride_id


def dismiss_visible_ride(
    db: Session,
    *,
    ride_id: int,
    driver_id: int,
    reason: str | None = None,
    ttl_seconds: int = RIDE_HIDE_TTL_SECONDS,
    policy_version: str = DISPATCH_POLICY_VERSION,
) -> RideVisibility:
    now = utc_now_naive()
    expires_at = now + timedelta(seconds=ttl_seconds)
    visibility = (
        db.query(RideVisibility)
        .filter(RideVisibility.ride_id == ride_id, RideVisibility.driver_id == driver_id)
        .first()
    )
    if visibility:
        visibility.dismissed_at = now
        visibility.last_seen_at = now
        visibility.expires_at = expires_at
        visibility.status = "hidden_by_driver"
        visibility.reason = reason
        visibility.correlation_id = visibility.correlation_id or uuid4().hex
        return visibility

    visibility = RideVisibility(
        ride_id=ride_id,
        driver_id=driver_id,
        first_seen_at=now,
        last_seen_at=now,
        dismissed_at=now,
        expires_at=expires_at,
        status="hidden_by_driver",
        reason=reason,
        ordering_rank=0,
        policy_version=policy_version,
        metadata_json=json.dumps({"source": "POST /drivers/rides/{ride_id}/hide"}),
        correlation_id=uuid4().hex,
    )
    db.add(visibility)
    return visibility


def active_hidden_filter(now: datetime | None = None):
    now = now or utc_now_naive()
    return and_(
        RideVisibility.dismissed_at.is_not(None),
        RideVisibility.status == "hidden_by_driver",
        or_(RideVisibility.expires_at.is_(None), RideVisibility.expires_at > now),
    )


def record_claim_attempt(
    db: Session,
    *,
    ride_id: int,
    driver_id: int,
    outcome: str,
    competing_driver_id: int | None = None,
    reason: str | None = None,
    policy_version: str = DISPATCH_POLICY_VERSION,
) -> RideClaimAttempt:
    attempt = RideClaimAttempt(
        ride_id=ride_id,
        driver_id=driver_id,
        outcome=outcome,
        competing_driver_id=competing_driver_id,
        reason=reason,
        policy_version=policy_version,
    )
    db.add(attempt)
    record_metric(db, "claim_attempts", 1.0, ride_id=ride_id, driver_id=driver_id)
    if outcome != "won":
        record_metric(db, "failed_claim_attempts", 1.0, ride_id=ride_id, driver_id=driver_id)
    return attempt


def record_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    event_type: str,
    actor_id: int | None = None,
    payload: dict | None = None,
    policy_version: str | None = None,
) -> Event:
    event = Event(
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        actor_id=actor_id,
        payload_json=json.dumps(payload or {}, sort_keys=True),
        policy_version=policy_version,
    )
    db.add(event)
    _append_marketplace_event_for_domain_event(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        actor_id=actor_id,
        payload=payload,
        policy_version=policy_version,
    )
    return event


def _append_marketplace_event_for_domain_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    event_type: str,
    actor_id: int | None,
    payload: dict | None,
    policy_version: str | None,
) -> None:
    marketplace_event_types = {
        "ride.created",
        "ride.accepted",
        "ride.arrived_pickup",
        "ride.started",
        "ride.completed",
        "ride.cancelled",
        "ride.hidden",
        "presence.changed",
        "presence.heartbeat",
        "earning.calculated",
    }
    if event_type not in marketplace_event_types:
        return

    from services.ledger import append_marketplace_event

    ride_id = entity_id if entity_type in {"ride", "earning"} else None
    driver_id = actor_id if entity_type in {"driver_presence", "earning"} else None
    event_payload = payload or {}
    append_marketplace_event(
        db,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        ride_id=ride_id,
        actor_id=actor_id,
        driver_id=driver_id,
        correlation_id=event_payload.get("visibility_correlation_id") or event_payload.get("correlation_id"),
        payload=event_payload,
        policy_version=policy_version or DISPATCH_POLICY_VERSION,
    )


def record_accept_metrics(db: Session, *, ride: Ride, driver_id: int) -> None:
    seconds = _seconds_between(ride.created_at, ride.accepted_at)
    if seconds is None:
        return
    record_metric(db, "time_to_accept", seconds, ride_id=ride.id, driver_id=driver_id)
    record_metric(db, "requested_to_accepted_latency", seconds, ride_id=ride.id, driver_id=driver_id)
    record_metric(db, "time_to_match", seconds, ride_id=ride.id, driver_id=driver_id)
    seen_count = (
        db.query(func.count(func.distinct(RideVisibility.driver_id)))
        .filter(RideVisibility.ride_id == ride.id)
        .scalar()
        or 0
    )
    record_metric(db, "drivers_who_saw_ride", float(seen_count), ride_id=ride.id, driver_id=driver_id)
    visible_count = (
        db.query(func.count(func.distinct(RideVisibility.ride_id)))
        .filter(RideVisibility.driver_id == driver_id)
        .scalar()
        or 0
    )
    wins = (
        db.query(func.count(func.distinct(RideClaimAttempt.ride_id)))
        .filter(RideClaimAttempt.driver_id == driver_id, RideClaimAttempt.outcome == "won")
        .scalar()
        or 0
    )
    if visible_count:
        record_metric(db, "acceptance_rate", wins / visible_count, driver_id=driver_id)


def record_started_metrics(db: Session, *, ride: Ride, driver_id: int) -> None:
    pickup_seconds = _seconds_between(ride.accepted_at, ride.arrived_pickup_at)
    if pickup_seconds is not None:
        record_metric(
            db,
            "accepted_to_pickup_arrival_latency",
            pickup_seconds,
            ride_id=ride.id,
            driver_id=driver_id,
        )
    start_seconds = _seconds_between(ride.accepted_at, ride.started_at)
    if start_seconds is not None:
        record_metric(db, "accepted_to_start_seconds", start_seconds, ride_id=ride.id, driver_id=driver_id)


def record_completed_metrics(db: Session, *, ride: Ride, driver_id: int) -> None:
    seconds = _seconds_between(ride.started_at, ride.completed_at)
    if seconds is not None:
        record_metric(db, "pickup_to_completion_duration", seconds, ride_id=ride.id, driver_id=driver_id)


def get_system_health_snapshot(db: Session) -> dict:
    active_statuses = (
        to_storage_ride_status(RideStatus.ACCEPTED),
        to_storage_ride_status(RideStatus.DRIVER_ARRIVED),
        to_storage_ride_status(RideStatus.IN_PROGRESS),
    )
    active_rides = db.query(Ride).filter(Ride.status.in_(active_statuses)).count()
    pending_rides = db.query(Ride).filter(
        Ride.status == to_storage_ride_status(RideStatus.REQUESTED),
        Ride.driver_id.is_(None),
    ).count()
    from services.driver_approval import query_dispatch_available_driver_ids

    available_drivers = len(query_dispatch_available_driver_ids(db))
    avg_match_time = (
        db.query(func.avg(Metric.value))
        .filter(Metric.metric_name == "time_to_accept")
        .scalar()
    )

    total_attempts = db.query(RideClaimAttempt).count()
    conflict_attempts = (
        db.query(RideClaimAttempt)
        .filter(RideClaimAttempt.outcome.in_(("conflict", "lost")))
        .count()
    )
    conflict_rate = conflict_attempts / total_attempts if total_attempts else 0.0

    return {
        "active_rides": active_rides,
        "pending_rides": pending_rides,
        "rides_waiting": pending_rides,
        "available_drivers": available_drivers,
        "driver_availability": {"available": available_drivers},
        "dispatch_conflicts": conflict_attempts,
        "avg_match_time": round(float(avg_match_time or 0.0), 2),
        "average_match_time_seconds": round(float(avg_match_time or 0.0), 2),
        "conflict_rate": round(conflict_rate, 4),
        "top_inefficiencies": get_top_inefficiencies(db),
    }


def get_driver_performance_snapshot(db: Session, *, driver_id: int) -> dict:
    avg_accept_time = (
        db.query(func.avg(Metric.value))
        .filter(Metric.metric_name == "time_to_accept", Metric.driver_id == driver_id)
        .scalar()
    )

    visible_ride_ids = {
        row[0]
        for row in db.query(RideVisibility.ride_id)
        .filter(RideVisibility.driver_id == driver_id)
        .distinct()
        .all()
    }
    won_ride_ids = {
        row[0]
        for row in db.query(RideClaimAttempt.ride_id)
        .filter(RideClaimAttempt.driver_id == driver_id, RideClaimAttempt.outcome == "won")
        .distinct()
        .all()
    }
    conflict_losses = (
        db.query(RideClaimAttempt)
        .filter(
            RideClaimAttempt.driver_id == driver_id,
            RideClaimAttempt.outcome.in_(("conflict", "lost")),
        )
        .count()
    )

    return {
        "avg_accept_time": round(float(avg_accept_time or 0.0), 2),
        "missed_rides": len(visible_ride_ids - won_ride_ids),
        "conflict_losses": conflict_losses,
    }


def get_driver_insights(db: Session, *, driver_id: int) -> dict:
    now = utc_now_naive()
    recent_cutoff = now - timedelta(minutes=10)
    visible_recent = (
        db.query(RideVisibility)
        .filter(RideVisibility.driver_id == driver_id, RideVisibility.last_seen_at >= recent_cutoff)
        .all()
    )
    attempted_recent = {
        row[0]
        for row in db.query(RideClaimAttempt.ride_id)
        .filter(RideClaimAttempt.driver_id == driver_id, RideClaimAttempt.attempted_at >= recent_cutoff)
        .all()
    }
    missed_recent = [record for record in visible_recent if record.ride_id not in attempted_recent]
    accept_times = [
        row[0]
        for row in db.query(Metric.value)
        .filter(Metric.driver_id == driver_id, Metric.metric_name == "time_to_accept")
        .order_by(Metric.timestamp.desc())
        .limit(20)
        .all()
    ]
    latest = accept_times[0] if accept_times else None
    previous = accept_times[1:]
    previous_avg = sum(previous) / len(previous) if previous else None
    conflict_losses = (
        db.query(RideClaimAttempt)
        .filter(RideClaimAttempt.driver_id == driver_id, RideClaimAttempt.outcome.in_(("conflict", "lost")))
        .count()
    )
    trend = {
        "type": "accept_time_trend",
        "status": "insufficient_data",
        "message": "Not enough measured accept-time history yet.",
        "evidence": {"time_to_accept_samples": len(accept_times)},
    }
    if latest is not None and previous_avg is not None:
        trend = {
            "type": "accept_time_trend",
            "status": "measured",
            "message": (
                "Your average accept time is slower than your past performance."
                if latest > previous_avg
                else "Your latest accept time is in line with or faster than your past performance."
            ),
            "evidence": {
                "latest_seconds": latest,
                "previous_average_seconds": round(previous_avg, 3),
            },
        }
    return {
        "driver_id": driver_id,
        "generated_at": now.isoformat(),
        "insights": [
            {
                "type": "missed_rides",
                "status": "measured",
                "message": f"You missed {len(missed_recent)} rides in the last 10 minutes.",
                "evidence": {"visibility_record_ids": [record.id for record in missed_recent]},
            },
            trend,
            {
                "type": "claim_conflicts",
                "status": "measured",
                "message": f"You tend to lose rides due to conflicts: {conflict_losses} conflict losses recorded.",
                "evidence": {"lost_claim_attempts": conflict_losses},
            },
        ],
    }


def get_ride_diagnostic(db: Session, *, ride: Ride) -> dict:
    now = utc_now_naive()
    attempts = db.query(RideClaimAttempt).filter(RideClaimAttempt.ride_id == ride.id).all()
    failed = [attempt for attempt in attempts if attempt.outcome != "won"]
    visible_drivers = (
        db.query(func.count(func.distinct(RideVisibility.driver_id)))
        .filter(RideVisibility.ride_id == ride.id)
        .scalar()
        or 0
    )
    time_to_match = _seconds_between(ride.created_at, ride.accepted_at)
    if ride.status == to_storage_ride_status(RideStatus.REQUESTED):
        time_in_requested_pool = _seconds_between(ride.created_at, now)
    else:
        time_in_requested_pool = _seconds_between(ride.created_at, ride.accepted_at)
    ignored = max(visible_drivers - len({attempt.driver_id for attempt in attempts}), 0)
    flags = []
    if time_to_match is not None and time_to_match > SLOW_MATCH_SECONDS:
        flags.append("slow_match")
    if ride.status == to_storage_ride_status(RideStatus.REQUESTED) and (time_in_requested_pool or 0) > ABANDONED_REQUEST_SECONDS:
        flags.append("abandoned_ride")
    if len(attempts) >= EXCESSIVE_COMPETITION_ATTEMPTS or len(failed) >= 2:
        flags.append("excessive_competition")
    return {
        "ride_id": ride.id,
        "status": ride.status,
        "time_to_match": time_to_match,
        "time_in_requested_pool": time_in_requested_pool,
        "number_of_drivers_who_ignored_it": ignored,
        "drivers_who_saw_ride": visible_drivers,
        "claim_attempts": len(attempts),
        "failed_claim_attempts": len(failed),
        "flags": flags,
        "evidence": {
            "created_at": ride.created_at.isoformat() if ride.created_at else None,
            "accepted_at": ride.accepted_at.isoformat() if ride.accepted_at else None,
            "attempt_ids": [attempt.id for attempt in attempts],
        },
    }


def get_top_inefficiencies(db: Session, *, limit: int = 10) -> list[dict]:
    rides = db.query(Ride).order_by(Ride.created_at.desc()).limit(200).all()
    diagnostics = [get_ride_diagnostic(db, ride=ride) for ride in rides]
    flagged = [item for item in diagnostics if item["flags"]]
    return sorted(
        flagged,
        key=lambda item: (
            len(item["flags"]),
            item.get("time_in_requested_pool") or item.get("time_to_match") or 0,
            item["failed_claim_attempts"],
        ),
        reverse=True,
    )[:limit]


def get_ride_transparency(db: Session, *, ride_id: int) -> dict | None:
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if ride is None:
        return None
    visibility = (
        db.query(RideVisibility)
        .filter(RideVisibility.ride_id == ride_id)
        .order_by(RideVisibility.first_seen_at.asc())
        .all()
    )
    attempts = (
        db.query(RideClaimAttempt)
        .filter(RideClaimAttempt.ride_id == ride_id)
        .order_by(RideClaimAttempt.attempted_at.asc())
        .all()
    )
    ledger_entries = (
        db.query(MarketplaceLedgerEntry)
        .filter(MarketplaceLedgerEntry.ride_id == ride_id)
        .order_by(MarketplaceLedgerEntry.id.asc())
        .all()
    )
    marketplace_ledger_events = (
        db.query(MarketplaceLedgerEvent)
        .filter(MarketplaceLedgerEvent.ride_id == ride_id)
        .order_by(MarketplaceLedgerEvent.id.asc())
        .all()
    )
    winner = next((attempt for attempt in attempts if attempt.outcome == "won"), None)
    conflict_attempts = [attempt for attempt in attempts if attempt.outcome in ("conflict", "lost")]
    latest_conflict = conflict_attempts[-1] if conflict_attempts else None
    return {
        "ride_id": ride_id,
        "assigned_driver_id": ride.driver_id,
        "why_this_driver_got_it": (
            "first successful atomic claim on the ranked open board"
            if ride.driver_id
            else "unassigned: no successful claim is recorded"
        ),
        "first_to_claim_driver_id": winner.driver_id if winner else None,
        "claim_winner_driver_id": winner.driver_id if winner else None,
        "claim_lost_driver_ids": [attempt.driver_id for attempt in conflict_attempts],
        "competitors": max(len({attempt.driver_id for attempt in attempts}) - (1 if winner else 0), 0),
        "driver_visibility": [
            {
                "ride_visibility_id": record.id,
                "driver_id": record.driver_id,
                "visible_from": record.first_seen_at.isoformat() if record.first_seen_at else None,
                "last_seen_at": record.last_seen_at.isoformat() if record.last_seen_at else None,
                "status": record.status,
                "ordering_rank": record.ordering_rank,
                "ordering_score": record.ordering_score,
                "why_this_rank": json.loads(record.why_this_rank_json or "{}"),
                "dispatch_policy_id": record.policy_version,
                "dispatch_policy_name": json.loads(record.metadata_json or "{}").get(
                    "dispatch_policy_name", DISPATCH_POLICY_NAME
                ),
                "ordered_by": json.loads(record.metadata_json or "{}").get("ordered_by", list(DISPATCH_ORDERING_RULE)),
                "visibility_reason": json.loads(record.metadata_json or "{}").get(
                    "visibility_reason", DISPATCH_VISIBILITY_REASON
                ),
                "correlation_id": record.correlation_id,
                "dismissed_at": record.dismissed_at.isoformat() if record.dismissed_at else None,
                "expires_at": record.expires_at.isoformat() if record.expires_at else None,
                "hide_reason": record.reason,
            }
            for record in visibility
        ],
        "claim_attempts": [
            {
                "claim_attempt_id": attempt.id,
                "driver_id": attempt.driver_id,
                "attempted_at": attempt.attempted_at.isoformat() if attempt.attempted_at else None,
                "outcome": attempt.outcome,
                "reason": attempt.reason,
                "competing_driver_id": attempt.competing_driver_id,
                "policy_version": attempt.policy_version,
                "http_status": 409 if attempt.outcome in ("conflict", "lost", "unavailable") else 200,
            }
            for attempt in attempts
        ],
        "claim_conflict": {
            "http_status": 409,
            "reason": latest_conflict.reason if latest_conflict else None,
            "competing_driver_id": latest_conflict.competing_driver_id if latest_conflict else None,
            "losing_driver_id": latest_conflict.driver_id if latest_conflict else None,
        }
        if latest_conflict
        else None,
        "ledger_entries": [
            {
                "ledger_entry_id": entry.id,
                "event_type": entry.event_type,
                "driver_id": entry.driver_id,
                "actor_id": entry.actor_id,
                "outcome": entry.outcome,
                "reason": entry.reason,
                "policy_version": entry.policy_version,
            }
            for entry in ledger_entries
        ],
        "marketplace_ledger_events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "driver_id": event.driver_id,
                "ride_id": event.ride_id,
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            }
            for event in marketplace_ledger_events
        ],
        "diagnostic": get_ride_diagnostic(db, ride=ride),
    }


def get_weekly_fairness_report(db: Session) -> dict:
    now = utc_now_naive()
    start = now - timedelta(days=7)
    waits = [
        row[0]
        for row in db.query(Metric.value)
        .filter(Metric.metric_name == "requested_to_accepted_latency", Metric.timestamp >= start)
        .all()
    ]
    counts = [
        count
        for _, count in db.query(RideVisibility.driver_id, func.count(RideVisibility.id))
        .filter(RideVisibility.first_seen_at >= start)
        .group_by(RideVisibility.driver_id)
        .all()
    ]
    consistency = None
    if counts:
        consistency = {
            "drivers_measured": len(counts),
            "average_visible_rides_per_driver": round(sum(counts) / len(counts), 3),
            "max_minus_min_visible_rides": max(counts) - min(counts),
        }
    return {
        "period_start": start.isoformat(),
        "period_end": now.isoformat(),
        "average_earnings_consistency": {
            "status": "unavailable",
            "reason": "completed ride fare totals exist, but no payout or earnings consistency ledger exists yet",
        },
        "average_wait_time_seconds": round(sum(waits) / len(waits), 3) if waits else None,
        "dispatch_fairness_consistency": consistency
        or {
            "status": "insufficient_data",
            "reason": "no ride visibility records in the selected period",
        },
    }