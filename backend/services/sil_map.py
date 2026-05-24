"""Build driver-visible SIL map/suggest responses (privacy + honesty gates)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.sil_cell_aggregate import SilCellAggregate
from services.sil_compute import compute_sil_bucket, confidence_band
from services.sil_gates import (
    busy_layer_min_k_met,
    cell_passes_confidence,
    slow_layer_min_k_met,
    thresholds,
)
from services.sil_h3 import cell_to_lat_lng
from services.sil_labels import (
    BUSY_LAYER_LABEL,
    LABEL_VERSION,
    SIL_MAP_DISCLAIMER,
    SLOW_LAYER_LABEL,
)


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    parts = [float(p.strip()) for p in bbox.split(",")]
    if len(parts) != 4:
        return None
    return parts[0], parts[1], parts[2], parts[3]


def _in_bbox(lat: float, lng: float, bbox: tuple[float, float, float, float]) -> bool:
    min_lat, min_lng, max_lat, max_lng = bbox
    return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng


def build_sil_map_response(
    db: Session,
    *,
    bbox: str | None = None,
    window_minutes: int = 30,
    bucket_minutes: int = 5,
    layers: str = "busy,slow",
    min_conf: float = 0.4,
) -> dict:
    bucket_start = compute_sil_bucket(
        db, window_minutes=window_minutes, bucket_minutes=bucket_minutes
    )
    layer_set = {s.strip().lower() for s in layers.split(",") if s.strip()}
    bbox_tuple = _parse_bbox(bbox)

    rows = (
        db.query(SilCellAggregate)
        .filter(SilCellAggregate.bucket_start_ts == bucket_start)
        .all()
    )

    cells_out: list[dict] = []
    not_enough: list[dict] = []

    for row in rows:
        lat, lng = cell_to_lat_lng(row.h3)
        if bbox_tuple and not _in_bbox(lat, lng, bbox_tuple):
            continue

        slow_ok = (
            "slow" in layer_set
            and slow_layer_min_k_met(
                unique_drivers=row.unique_drivers, fleet_samples=row.fleet_samples
            )
            and row.congestion_score >= 0.25
        )
        busy_ok = (
            "busy" in layer_set
            and busy_layer_min_k_met(demand_count=row.demand_count)
            and row.busy_score >= 0.25
        )

        if not row.min_k_met or not cell_passes_confidence(row.confidence, min_conf):
            not_enough.append({"h3": row.h3, "lat": lat, "lng": lng})
            continue

        if not slow_ok and not busy_ok:
            not_enough.append({"h3": row.h3, "lat": lat, "lng": lng})
            continue

        cell_payload = {
            "h3": row.h3,
            "lat": lat,
            "lng": lng,
            "confidence": round(float(row.confidence), 3),
            "confidence_band": confidence_band(row.confidence),
            "labels": {
                "busy": BUSY_LAYER_LABEL,
                "slow": SLOW_LAYER_LABEL,
            },
        }
        if slow_ok:
            cell_payload["congestion_score"] = round(float(row.congestion_score), 3)
        if busy_ok:
            cell_payload["busy_score"] = round(float(row.busy_score), 3)

        cells_out.append(cell_payload)

    return {
        "bucket_start_ts": bucket_start.isoformat() + "Z",
        "bucket_minutes": bucket_minutes,
        "window_minutes": window_minutes,
        "label_version": LABEL_VERSION,
        "disclaimer": SIL_MAP_DISCLAIMER,
        "labels": {
            "busy": BUSY_LAYER_LABEL,
            "slow": SLOW_LAYER_LABEL,
        },
        "thresholds": thresholds(),
        "cells": cells_out,
        "not_enough_data_areas": not_enough,
        "layers": sorted(layer_set),
    }


def build_sil_suggest_response(
    db: Session,
    *,
    driver_h3: str,
    horizon_minutes: int = 15,
) -> dict:
    compute_sil_bucket(db, window_minutes=30, bucket_minutes=5)
    rows = (
        db.query(SilCellAggregate)
        .order_by(SilCellAggregate.busy_score.desc())
        .limit(50)
        .all()
    )
    suggestions: list[dict] = []
    for row in rows:
        if not row.min_k_met or row.confidence < 0.4:
            continue
        if row.h3 == driver_h3:
            continue
        lat, lng = cell_to_lat_lng(row.h3)
        suggestions.append(
            {
                "target_h3": row.h3,
                "lat": lat,
                "lng": lng,
                "score": round(float(row.busy_score), 3),
                "reason": "Higher busy score nearby with sufficient confidence.",
                "confidence": confidence_band(row.confidence),
            }
        )
        if len(suggestions) >= 5:
            break

    return {
        "horizon_minutes": horizon_minutes,
        "suggestions": suggestions,
        "label_version": LABEL_VERSION,
    }
