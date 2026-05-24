"""Compute CRL cell snapshots, time baselines, and explanations."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy.orm import Session

from models.crl_cell_explanation import CrlCellExplanation
from models.crl_cell_snapshot import CrlCellSnapshot
from models.crl_time_pattern import CrlTimePattern
from models.driver_telemetry_point import DriverTelemetryPoint
from models.ride import Ride
from models.user import User
from services.crl_attribution import attribute_cell
from services.crl_zones import ensure_default_zones, zones_for_cell
from services.datetime_utils import utc_now_naive
from services.lifecycle import RideStatus, to_storage_ride_status
from services.sil_gates import MIN_DEMAND_COUNT, busy_layer_min_k_met, cell_passes_confidence
from services.sil_h3 import DEFAULT_H3_RES, lat_lng_to_cell


@dataclass
class _Scratch:
    demand: int = 0
    pickups: int = 0
    dropoffs: int = 0
    cancels: int = 0
    wait_seconds: list[float] = field(default_factory=list)
    idle_drivers: int = 0
    driver_ids: set[int] = field(default_factory=set)


def _align_bucket_start(now, bucket_minutes: int):
    minute = (now.minute // bucket_minutes) * bucket_minutes
    return now.replace(minute=minute, second=0, microsecond=0)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _update_time_patterns(db: Session, since) -> None:
    """Rolling baseline from rides in lookback window."""
    rides = db.query(Ride).filter(Ride.created_at >= since).all()
    buckets: dict[tuple[str, int, int], list[tuple[int, int]]] = defaultdict(list)
    for ride in rides:
        if ride.pickup_latitude is None or ride.pickup_longitude is None:
            continue
        ts = ride.created_at or utc_now_naive()
        cell = lat_lng_to_cell(float(ride.pickup_latitude), float(ride.pickup_longitude))
        key = (cell, ts.hour, ts.weekday())
        buckets[key].append((1, 0))

    for (h3_cell, hour, dow), counts in buckets.items():
        avg_demand = sum(c[0] for c in counts) / max(len(counts), 1)
        row = (
            db.query(CrlTimePattern)
            .filter(
                CrlTimePattern.h3 == h3_cell,
                CrlTimePattern.hour_of_day == hour,
                CrlTimePattern.day_of_week == dow,
            )
            .first()
        )
        if row:
            row.avg_demand = avg_demand
        else:
            db.add(
                CrlTimePattern(
                    h3=h3_cell,
                    hour_of_day=hour,
                    day_of_week=dow,
                    avg_demand=avg_demand,
                    avg_supply=0.0,
                )
            )


def compute_crl_bucket(
    db: Session,
    *,
    window_minutes: int = 30,
    bucket_minutes: int = 5,
) -> datetime:
    ensure_default_zones(db)
    now = utc_now_naive()
    bucket_start = _align_bucket_start(now, bucket_minutes)
    since = now - timedelta(minutes=window_minutes)
    _update_time_patterns(db, since - timedelta(days=7))

    cells: dict[str, _Scratch] = defaultdict(_Scratch)

    open_statuses = {
        to_storage_ride_status(RideStatus.REQUESTED),
        to_storage_ride_status(RideStatus.OFFERED),
        "requested",
        "offered",
    }
    cancelled_status = to_storage_ride_status(RideStatus.CANCELLED)
    completed_status = to_storage_ride_status(RideStatus.COMPLETED)

    for ride in db.query(Ride).filter(Ride.created_at >= since).all():
        if ride.pickup_latitude is not None and ride.pickup_longitude is not None:
            pc = lat_lng_to_cell(float(ride.pickup_latitude), float(ride.pickup_longitude))
            sc = cells[pc]
            if ride.status in open_statuses:
                sc.demand += 1
                sc.pickups += 1
            elif ride.status == cancelled_status:
                sc.cancels += 1
            if ride.accepted_at and ride.created_at:
                sc.wait_seconds.append(
                    max(0.0, (ride.accepted_at - ride.created_at).total_seconds())
                )

        if ride.dropoff_latitude is not None and ride.dropoff_longitude is not None:
            if ride.status == completed_status:
                dc = lat_lng_to_cell(float(ride.dropoff_latitude), float(ride.dropoff_longitude))
                cells[dc].dropoffs += 1

    for driver in (
        db.query(User)
        .filter(User.availability.in_(("available", "online")))
        .filter(User.last_latitude.isnot(None))
        .all()
    ):
        dc = lat_lng_to_cell(float(driver.last_latitude), float(driver.last_longitude))
        cells[dc].idle_drivers += 1

    for point in db.query(DriverTelemetryPoint).filter(DriverTelemetryPoint.created_at >= since).all():
        cells[lat_lng_to_cell(point.lat, point.lng)].driver_ids.add(int(point.driver_id))

    db.query(CrlCellSnapshot).filter(CrlCellSnapshot.bucket_start_ts == bucket_start).delete(
        synchronize_session=False
    )
    db.query(CrlCellExplanation).filter(CrlCellExplanation.bucket_start_ts == bucket_start).delete(
        synchronize_session=False
    )

    hour, dow = now.hour, now.weekday()

    for h3_cell, sc in cells.items():
        total_events = sc.demand + sc.cancels
        cancel_rate = sc.cancels / max(total_events, 1)
        avg_wait = sum(sc.wait_seconds) / len(sc.wait_seconds) if sc.wait_seconds else None
        supply_ratio = sc.idle_drivers / max(sc.demand, 1)
        demand_score = _sigmoid((sc.demand - 0.5 * sc.idle_drivers) / 2.0)
        wait_score = min(1.0, (avg_wait or 0) / 600.0) if avg_wait else 0.0
        unique_drivers = len(sc.driver_ids)

        min_k_met = busy_layer_min_k_met(demand_count=sc.demand) and unique_drivers >= 1
        confidence = 0.0
        if min_k_met:
            confidence = min(
                1.0,
                sc.demand / max(MIN_DEMAND_COUNT, 1) * 0.6 + wait_score * 0.4,
            )
        if not cell_passes_confidence(confidence):
            min_k_met = False
            confidence = 0.0

        snap = CrlCellSnapshot(
            h3=h3_cell,
            bucket_start_ts=bucket_start,
            bucket_minutes=bucket_minutes,
            demand_count=sc.demand,
            pickup_count=sc.pickups,
            dropoff_count=sc.dropoffs,
            cancel_count=sc.cancels,
            cancel_rate=cancel_rate,
            avg_wait_seconds=avg_wait,
            idle_driver_count=sc.idle_drivers,
            supply_demand_ratio=supply_ratio,
            demand_score=demand_score,
            wait_score=wait_score,
            confidence=confidence,
            min_k_met=min_k_met,
            unique_drivers=unique_drivers,
            computed_at=now,
        )
        db.add(snap)
        db.flush()

        zones = zones_for_cell(db, h3_cell)
        expl = attribute_cell(db, snap, zones, hour=hour, dow=dow)
        db.add(
            CrlCellExplanation(
                h3=h3_cell,
                bucket_start_ts=bucket_start,
                primary_cause=expl["primary_cause"],
                secondary_causes_json=json.dumps(expl["secondary_causes"]),
                confidence=expl["confidence"],
                signals_used_json=json.dumps(expl["signals_used"]),
                driver_label=expl["driver_label"],
                label_version=expl["label_version"],
            )
        )

    db.commit()
    return bucket_start
