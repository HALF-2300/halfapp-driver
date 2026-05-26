"""Driver and operator CRL API payloads."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.crl_cell_explanation import CrlCellExplanation
from models.crl_cell_snapshot import CrlCellSnapshot
from services.crl_snapshot import CrlSource, resolve_crl_bucket
from services.crl_labels import CRL_DISCLAIMER, CRL_OPERATOR_DISCLAIMER, NOT_ENOUGH_DATA_LABEL
from services.sil_h3 import cell_to_lat_lng


def build_crl_map_response(
    db: Session,
    *,
    window_minutes: int = 30,
    min_conf: float = 0.4,
) -> tuple[dict, CrlSource]:
    bucket_start, source = resolve_crl_bucket(db, window_minutes=window_minutes)
    snaps = (
        db.query(CrlCellSnapshot)
        .filter(CrlCellSnapshot.bucket_start_ts == bucket_start)
        .all()
    )
    explains = {
        (e.h3, e.bucket_start_ts): e
        for e in db.query(CrlCellExplanation)
        .filter(CrlCellExplanation.bucket_start_ts == bucket_start)
        .all()
    }

    cells_out: list[dict] = []
    not_enough: list[dict] = []

    for snap in snaps:
        lat, lng = cell_to_lat_lng(snap.h3)
        expl = explains.get((snap.h3, snap.bucket_start_ts))

        if not snap.min_k_met or snap.confidence < min_conf or expl is None:
            not_enough.append({"h3": snap.h3, "lat": lat, "lng": lng})
            continue

        cells_out.append(
            {
                "h3": snap.h3,
                "lat": lat,
                "lng": lng,
                "demand_score": round(float(snap.demand_score), 3),
                "wait_score": round(float(snap.wait_score), 3),
                "primary_cause": expl.primary_cause,
                "secondary_causes": json_load_list(expl.secondary_causes_json),
                "confidence": round(float(expl.confidence), 3),
                "label": expl.driver_label,
            }
        )

    return (
        {
            "bucket_start_ts": bucket_start.isoformat() + "Z",
            "window_minutes": window_minutes,
            "disclaimer": CRL_DISCLAIMER,
            "cells": cells_out,
            "not_enough_data_areas": not_enough,
            "not_enough_data_label": NOT_ENOUGH_DATA_LABEL,
        },
        source,
    )


def build_crl_explain_response(db: Session, *, h3_cell: str) -> tuple[dict | None, CrlSource]:
    _, source = resolve_crl_bucket(db)
    expl = (
        db.query(CrlCellExplanation)
        .filter(CrlCellExplanation.h3 == h3_cell)
        .order_by(CrlCellExplanation.bucket_start_ts.desc())
        .first()
    )
    snap = (
        db.query(CrlCellSnapshot)
        .filter(CrlCellSnapshot.h3 == h3_cell)
        .order_by(CrlCellSnapshot.bucket_start_ts.desc())
        .first()
    )
    if not expl or not snap:
        return None, source
    if not snap.min_k_met:
        return (
            {
                "h3": h3_cell,
                "not_enough_data": True,
                "label": NOT_ENOUGH_DATA_LABEL,
                "disclaimer": CRL_DISCLAIMER,
            },
            source,
        )

    return (
        {
            "h3": h3_cell,
            "primary_cause": expl.primary_cause,
            "secondary_causes": json_load_list(expl.secondary_causes_json),
            "signals_used": json_load_dict(expl.signals_used_json),
            "confidence": round(float(expl.confidence), 3),
            "label": expl.driver_label,
            "disclaimer": CRL_DISCLAIMER,
        },
        source,
    )


def build_crl_admin_overview(db: Session) -> tuple[dict, CrlSource]:
    bucket_start, source = resolve_crl_bucket(db)
    explains = (
        db.query(CrlCellExplanation)
        .filter(CrlCellExplanation.bucket_start_ts == bucket_start)
        .all()
    )
    cause_counts: dict[str, int] = {}
    for e in explains:
        cause_counts[e.primary_cause] = cause_counts.get(e.primary_cause, 0) + 1
    total = max(len(explains), 1)
    breakdown = [
        {"cause": k, "share": round(v / total, 3)}
        for k, v in sorted(cause_counts.items(), key=lambda x: -x[1])
    ]
    anomaly = [
        {
            "h3": e.h3,
            "primary_cause": e.primary_cause,
            "confidence": e.confidence,
            "label": e.driver_label,
        }
        for e in explains
        if e.confidence >= 0.6
    ][:20]
    return (
        {
            "bucket_start_ts": bucket_start.isoformat() + "Z",
            "disclaimer": CRL_OPERATOR_DISCLAIMER,
            "cause_breakdown": breakdown,
            "anomaly_cells": anomaly,
        },
        source,
    )


def json_load_list(raw: str | None) -> list:
    import json

    if not raw:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else []
    except json.JSONDecodeError:
        return []


def json_load_dict(raw: str | None) -> dict:
    import json

    if not raw:
        return {}
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else {}
    except json.JSONDecodeError:
        return {}
