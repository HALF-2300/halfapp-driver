"""Aggregate fleet GPS speeds into heatmap points (no external traffic API)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from models.driver_telemetry_point import DriverTelemetryPoint
from services.datetime_utils import utc_now_naive


def build_fleet_traffic_heatmap(
    db: Session,
    *,
    minutes: int = 10,
    precision: float = 0.002,
) -> dict:
    """
    Returns {points: [[lat, lng, intensity], ...], window_minutes, freeflow_mps?}.
    intensity 0..1 where 1 = much slower than fleet free-flow estimate.
    """
    minutes = max(1, min(int(minutes), 120))
    precision = max(0.0005, min(float(precision), 0.02))
    since = utc_now_naive() - timedelta(minutes=minutes)

    rows = (
        db.query(DriverTelemetryPoint)
        .filter(DriverTelemetryPoint.created_at >= since)
        .all()
    )
    if not rows:
        return {"points": [], "window_minutes": minutes}

    buckets: dict[tuple[float, float], tuple[float, int]] = {}
    for row in rows:
        if row.speed_mps is None:
            continue
        key_lat = round(row.lat / precision) * precision
        key_lng = round(row.lng / precision) * precision
        key = (key_lat, key_lng)
        total, count = buckets.get(key, (0.0, 0))
        buckets[key] = (total + float(row.speed_mps), count + 1)

    if not buckets:
        return {"points": [], "window_minutes": minutes}

    speeds = sorted(s / max(c, 1) for s, c in buckets.values())
    freeflow = speeds[int(len(speeds) * 0.9)] if speeds else 10.0
    freeflow = max(freeflow, 3.0)

    points: list[list[float]] = []
    for (lat, lng), (total, count) in buckets.items():
        avg = total / max(count, 1)
        ratio = min(avg / freeflow, 1.0)
        intensity = 1.0 - ratio
        if intensity >= 0.25:
            points.append([lat, lng, float(intensity)])

    return {
        "points": points,
        "window_minutes": minutes,
        "freeflow_mps": float(freeflow),
    }
