"""Rule-based cause attribution engine (CRL v0.1)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models.city_event import CityEvent
from models.crl_cell_snapshot import CrlCellSnapshot
from models.crl_time_pattern import CrlTimePattern
from models.zone_catalog import ZoneCatalog
from services import crl_causes as causes
from services.crl_causes import driver_label_for_cause
from services.crl_labels import CRL_LABEL_VERSION
from services.datetime_utils import utc_now_naive
from services.sil_h3 import cell_to_lat_lng


@dataclass
class _CauseScore:
    cause: str
    score: float
    signal_key: str
    signal_value: float | str


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p = math.pi / 180.0
    a = (
        math.sin((lat2 - lat1) * p / 2) ** 2
        + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lng2 - lng1) * p / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _active_events(db: Session, now) -> list[CityEvent]:
    return (
        db.query(CityEvent)
        .filter(CityEvent.start_ts <= now, CityEvent.end_ts >= now)
        .all()
    )


def _event_near_cell(db: Session, h3_cell: str, events: list[CityEvent]) -> CityEvent | None:
    lat, lng = cell_to_lat_lng(h3_cell)
    for ev in events:
        if ev.h3_center == h3_cell:
            return ev
        if ev.center_lat is not None and ev.center_lng is not None:
            radius = ev.radius_m or 1500.0
            if _haversine_m(lat, lng, ev.center_lat, ev.center_lng) <= radius:
                return ev
    return None


def _baseline_for_cell(
    db: Session, h3_cell: str, hour: int, dow: int
) -> CrlTimePattern | None:
    return (
        db.query(CrlTimePattern)
        .filter(
            CrlTimePattern.h3 == h3_cell,
            CrlTimePattern.hour_of_day == hour,
            CrlTimePattern.day_of_week == dow,
        )
        .first()
    )


def attribute_cell(
    db: Session,
    snapshot: CrlCellSnapshot,
    zones: list[ZoneCatalog],
    *,
    hour: int,
    dow: int,
) -> dict:
    """Return explanation dict ready for persistence / API."""
    now = utc_now_naive()
    events = _active_events(db, now)
    baseline = _baseline_for_cell(db, snapshot.h3, hour, dow)

    scores: list[_CauseScore] = []

    base_demand = (baseline.avg_demand if baseline else 0.0) or 1.0
    demand_ratio = snapshot.demand_count / max(base_demand, 1.0)
    if demand_ratio >= 1.5:
        if 6 <= hour <= 10:
            scores.append(
                _CauseScore(causes.MORNING_COMMUTE, 0.75 * min(demand_ratio / 2, 1.0), "demand_vs_baseline", demand_ratio)
            )
        elif 16 <= hour <= 20:
            scores.append(
                _CauseScore(causes.EVENING_COMMUTE, 0.75 * min(demand_ratio / 2, 1.0), "demand_vs_baseline", demand_ratio)
            )
        else:
            scores.append(
                _CauseScore(causes.UNCERTAIN_PATTERN, 0.4, "demand_vs_baseline", demand_ratio)
            )

    for zone in zones:
        zt = zone.zone_type
        if zt == "airport" or zt == "transport":
            if snapshot.dropoff_count > snapshot.pickup_count * 1.2:
                scores.append(
                    _CauseScore(
                        causes.TRANSPORT_HUB_ARRIVAL,
                        0.7 * zone.priority_weight,
                        "zone_type",
                        f"{zone.zone_id}:arrival_flow",
                    )
                )
            if snapshot.pickup_count > snapshot.dropoff_count * 1.2:
                scores.append(
                    _CauseScore(
                        causes.TRANSPORT_HUB_DEPARTURE,
                        0.65 * zone.priority_weight,
                        "zone_type",
                        f"{zone.zone_id}:departure_flow",
                    )
                )

    ratio = snapshot.supply_demand_ratio
    if ratio is not None and ratio < 0.5 and snapshot.demand_count >= 2:
        wait = snapshot.avg_wait_seconds or 0
        if wait >= 180 or snapshot.idle_driver_count <= 1:
            scores.append(
                _CauseScore(causes.DRIVER_SHORTAGE, 0.72, "supply_demand_ratio", ratio)
            )

    if snapshot.cancel_rate >= 0.25 and snapshot.cancel_count >= 1:
        scores.append(
            _CauseScore(causes.MATCH_FRICTION, 0.6, "cancel_rate", snapshot.cancel_rate)
        )

    ev = _event_near_cell(db, snapshot.h3, events)
    if ev is not None:
        scores.append(
            _CauseScore(causes.EVENT_DRIVEN, 0.65 * float(ev.confidence), "event_id", ev.event_id)
        )

    if snapshot.pickup_count > snapshot.dropoff_count * 1.5 and snapshot.pickup_count >= 2:
        scores.append(
            _CauseScore(causes.PICKUP_SOURCE_ZONE, 0.55, "pickup_vs_dropoff", snapshot.pickup_count)
        )
    if snapshot.dropoff_count > snapshot.pickup_count * 1.5 and snapshot.dropoff_count >= 2:
        scores.append(
            _CauseScore(causes.DROPOFF_SINK_ZONE, 0.55, "dropoff_vs_pickup", snapshot.dropoff_count)
        )

    scores.sort(key=lambda s: s.score, reverse=True)
    if not scores or scores[0].score < 0.35:
        primary = causes.UNCERTAIN_PATTERN
        secondary: list[str] = []
        confidence = 0.25
    else:
        primary = scores[0].cause
        secondary = [s.cause for s in scores[1:3] if s.score >= 0.4]
        confidence = min(0.95, scores[0].score)

    signals_used = {
        s.signal_key: s.signal_value for s in scores[:6]
    }
    signals_used["demand_count_band"] = "low" if snapshot.demand_count < 5 else "medium"
    signals_used["hour_of_day"] = hour
    signals_used["day_of_week"] = dow
    if baseline:
        signals_used["baseline_avg_demand"] = baseline.avg_demand

    label = driver_label_for_cause(primary, secondary)

    return {
        "primary_cause": primary,
        "secondary_causes": secondary,
        "confidence": round(confidence, 3),
        "signals_used": signals_used,
        "driver_label": label,
        "label_version": CRL_LABEL_VERSION,
    }
