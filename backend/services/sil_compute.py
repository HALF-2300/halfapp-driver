"""Compute SIL hex aggregates from rides, telemetry, and online drivers."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from statistics import median

from sqlalchemy.orm import Session

from models.driver_telemetry_point import DriverTelemetryPoint
from models.ride import Ride
from models.sil_cell_aggregate import SilCellAggregate
from models.user import User
from services.datetime_utils import utc_now_naive
from services.lifecycle import RideStatus, to_storage_ride_status
from services.sil_gates import (
    busy_layer_min_k_met,
    cell_passes_confidence,
    slow_layer_min_k_met,
)
from services.sil_h3 import DEFAULT_H3_RES, lat_lng_to_cell
from services.sil_labels import LABEL_VERSION


@dataclass
class _CellScratch:
    demand_count: int = 0
    supply_idle_count: int = 0
    speeds: list[float] = field(default_factory=list)
    driver_ids: set[int] = field(default_factory=set)


def _align_bucket_start(now, bucket_minutes: int):
    minute = (now.minute // bucket_minutes) * bucket_minutes
    return now.replace(minute=minute, second=0, microsecond=0)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def compute_sil_bucket(
    db: Session,
    *,
    window_minutes: int = 30,
    bucket_minutes: int = 5,
    h3_res: int | None = None,
) -> datetime:
    """Recompute aggregates for the current bucket; returns bucket_start_ts."""
    h3_res = h3_res if h3_res is not None else DEFAULT_H3_RES
    now = utc_now_naive()
    bucket_start = _align_bucket_start(now, bucket_minutes)
    since = now - timedelta(minutes=window_minutes)

    cells: dict[str, _CellScratch] = defaultdict(_CellScratch)

    demand_statuses = {
        to_storage_ride_status(RideStatus.REQUESTED),
        to_storage_ride_status(RideStatus.OFFERED),
        "requested",
        "offered",
    }
    rides = (
        db.query(Ride)
        .filter(Ride.created_at >= since)
        .filter(Ride.status.in_(list(demand_statuses)))
        .all()
    )
    for ride in rides:
        if ride.pickup_latitude is None or ride.pickup_longitude is None:
            continue
        cell = lat_lng_to_cell(float(ride.pickup_latitude), float(ride.pickup_longitude), h3_res)
        cells[cell].demand_count += 1

    online_drivers = (
        db.query(User)
        .filter(User.availability.in_(("available", "online")))
        .filter(User.last_latitude.isnot(None))
        .filter(User.last_longitude.isnot(None))
        .all()
    )
    for driver in online_drivers:
        cell = lat_lng_to_cell(float(driver.last_latitude), float(driver.last_longitude), h3_res)
        cells[cell].supply_idle_count += 1

    telemetry = (
        db.query(DriverTelemetryPoint)
        .filter(DriverTelemetryPoint.created_at >= since)
        .all()
    )
    for point in telemetry:
        cell = lat_lng_to_cell(float(point.lat), float(point.lng), h3_res)
        scratch = cells[cell]
        scratch.driver_ids.add(int(point.driver_id))
        if point.speed_mps is not None:
            scratch.speeds.append(float(point.speed_mps))

    db.query(SilCellAggregate).filter(
        SilCellAggregate.bucket_start_ts == bucket_start
    ).delete(synchronize_session=False)

    for h3_cell, scratch in cells.items():
        fleet_samples = len(scratch.speeds)
        unique_drivers = len(scratch.driver_ids)
        p50 = float(median(scratch.speeds)) if scratch.speeds else None

        baseline = 10.0
        if scratch.speeds:
            sorted_speeds = sorted(scratch.speeds)
            baseline = max(sorted_speeds[int(len(sorted_speeds) * 0.9)], 3.0)

        congestion = 0.0
        if p50 is not None and baseline > 0:
            congestion = max(0.0, min(1.0, 1.0 - (p50 / baseline)))

        busy = _sigmoid((scratch.demand_count - 0.5 * scratch.supply_idle_count) / 2.0)

        slow_ok = slow_layer_min_k_met(
            unique_drivers=unique_drivers, fleet_samples=fleet_samples
        )
        busy_ok = busy_layer_min_k_met(demand_count=scratch.demand_count)
        min_k_met = slow_ok or busy_ok

        from services.sil_gates import MIN_DEMAND_COUNT, MIN_FLEET_SAMPLES

        confidence = 0.0
        if min_k_met:
            confidence = min(
                1.0,
                (fleet_samples / max(MIN_FLEET_SAMPLES, 1)) * 0.5
                + (scratch.demand_count / max(MIN_DEMAND_COUNT, 1)) * 0.5,
            )

        if not cell_passes_confidence(confidence) and not min_k_met:
            confidence = 0.0

        provenance = {
            "demand": scratch.demand_count > 0,
            "fleet": fleet_samples > 0,
            "routing": False,
        }

        db.add(
            SilCellAggregate(
                h3=h3_cell,
                bucket_start_ts=bucket_start,
                bucket_minutes=bucket_minutes,
                demand_count=scratch.demand_count,
                supply_idle_count=scratch.supply_idle_count,
                fleet_samples=fleet_samples,
                unique_drivers=unique_drivers,
                fleet_speed_p50_mps=p50,
                congestion_score=congestion,
                busy_score=busy,
                confidence=confidence,
                min_k_met=min_k_met and cell_passes_confidence(confidence),
                provenance_json=json.dumps(provenance),
                label_version=LABEL_VERSION,
                computed_at=now,
            )
        )

    db.commit()
    return bucket_start


def confidence_band(value: float) -> str:
    if value >= 0.66:
        return "high"
    if value >= 0.4:
        return "medium"
    return "low"
