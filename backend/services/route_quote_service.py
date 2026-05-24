"""Route quotes with proof receipts (SIL v0.1)."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from models.proof_receipt import ProofReceipt
from models.route_quote import RouteQuote
from services.routing_service import HAVERSINE_FALLBACK_PROVIDER, route
from services.sil_gates import proof_level_for_route
from services.sil_h3 import lat_lng_to_cell
from services.sil_labels import (
    ETA_HONESTY_FALLBACK,
    ETA_HONESTY_OSRM,
    PROOF_BADGE_A,
    PROOF_BADGE_B,
    PROOF_BADGE_C,
    ROUTE_LABEL_FALLBACK,
    ROUTE_LABEL_OSRM,
)


def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _route_method_label(route_method: str, used_fallback: bool) -> str:
    if used_fallback or route_method == "fallback_straight_line":
        return ROUTE_LABEL_FALLBACK
    return ROUTE_LABEL_OSRM


def _eta_honesty(route_method: str, used_fallback: bool) -> str:
    if used_fallback or route_method == "fallback_straight_line":
        return ETA_HONESTY_FALLBACK
    return ETA_HONESTY_OSRM


def _proof_badge(proof_level: str) -> str:
    if proof_level == "A_ROAD_ACCURATE":
        return PROOF_BADGE_A
    if proof_level == "B_APPROXIMATE":
        return PROOF_BADGE_B
    return PROOF_BADGE_C


def create_route_quote(
    db: Session,
    *,
    driver_id: int,
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
) -> dict:
    estimate = route((from_lat, from_lng), (to_lat, to_lng))
    used_fallback = bool(estimate.used_fallback)
    route_method = (
        "fallback_straight_line"
        if used_fallback or estimate.route_provider == HAVERSINE_FALLBACK_PROVIDER
        else "osrm_route"
    )
    proof_level = proof_level_for_route(
        route_method=route_method, used_fallback=used_fallback
    )

    distance_m = round(float(estimate.distance_km) * 1000.0, 1)
    duration_s = int(estimate.duration_minutes) * 60

    honesty_flags = {
        "road_accurate": proof_level == "A_ROAD_ACCURATE",
        "live_traffic": False,
        "fleet_estimated_traffic_only": True,
    }

    payload = {
        "from": {"lat": round(from_lat, 6), "lng": round(from_lng, 6)},
        "to": {"lat": round(to_lat, 6), "lng": round(to_lng, 6)},
        "route_method": route_method,
        "route_provider": estimate.route_provider,
        "used_fallback": used_fallback,
        "distance_m_est": distance_m,
        "duration_s_est": duration_s,
        "honesty_flags": honesty_flags,
    }
    receipt_hash = _hash_payload(payload)

    quote = RouteQuote(
        driver_id=driver_id,
        from_h3=lat_lng_to_cell(from_lat, from_lng),
        to_h3=lat_lng_to_cell(to_lat, to_lng),
        route_method=route_method,
        distance_m_est=distance_m,
        duration_s_est=duration_s,
        geometry_json=None
        if used_fallback
        else json.dumps({"type": "pending", "provider": estimate.route_provider}),
        confidence=0.5 if used_fallback else 0.75,
        honesty_flags_json=json.dumps(honesty_flags),
    )
    db.add(quote)
    db.flush()

    receipt = ProofReceipt(
        subject="route_quote",
        subject_id=quote.id,
        proof_level=proof_level,
        proof_reason="OSRM route response"
        if proof_level == "A_ROAD_ACCURATE"
        else "Haversine fallback",
        receipt_payload_json=json.dumps(payload),
        receipt_hash=receipt_hash,
    )
    db.add(receipt)
    db.flush()
    quote.proof_receipt_id = receipt.id
    db.commit()
    db.refresh(quote)
    db.refresh(receipt)

    label = _route_method_label(route_method, used_fallback)
    return {
        "route_quote_id": quote.id,
        "route_method": route_method,
        "proof_level": proof_level,
        "proof_receipt_id": receipt.id,
        "distance_m_est": distance_m,
        "duration_s_est": duration_s,
        "label": label,
        "eta_honesty": _eta_honesty(route_method, used_fallback),
        "proof_badge": _proof_badge(proof_level),
        "honesty_flags": honesty_flags,
        "geometry": None if used_fallback else {"provider": estimate.route_provider},
    }


def get_proof_receipt_summary(db: Session, receipt_id: int) -> dict | None:
    receipt = db.query(ProofReceipt).filter(ProofReceipt.id == receipt_id).first()
    if receipt is None:
        return None
    payload = json.loads(receipt.receipt_payload_json)
    return {
        "id": receipt.id,
        "subject": receipt.subject,
        "subject_id": receipt.subject_id,
        "proof_level": receipt.proof_level,
        "proof_reason": receipt.proof_reason,
        "proof_badge": _proof_badge(receipt.proof_level),
        "receipt_hash": receipt.receipt_hash,
        "signed_by": receipt.signed_by,
        "created_at": receipt.created_at.isoformat() if receipt.created_at else None,
        "summary": {
            "route_method": payload.get("route_method"),
            "distance_m_est": payload.get("distance_m_est"),
            "duration_s_est": payload.get("duration_s_est"),
            "honesty_flags": payload.get("honesty_flags"),
        },
    }
