"""City Reality Layer — operator/admin API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.city_event import CityEvent
from services.crl_map import build_crl_admin_overview
from services.datetime_utils import utc_now_naive
from services.rbac import AuthPrincipal, load_principal_user, require_role
from services.sil_h3 import lat_lng_to_cell

router = APIRouter(prefix="/admin/crl", tags=["admin", "city-reality"])
ADMIN_ACCESS = require_role("admin")


class CityEventIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    event_type: str = Field(default="operator_entry", max_length=64)
    start_ts: datetime
    end_ts: datetime
    center_lat: float | None = None
    center_lng: float | None = None
    radius_m: float = Field(default=1500.0, ge=100.0, le=20000.0)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    notes: str | None = None


@router.get("/overview")
def crl_admin_overview(
    response: Response,
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    _ = load_principal_user(db, admin_user)
    body, source = build_crl_admin_overview(db)
    response.headers["X-CRL-Source"] = source
    return body


@router.post("/events")
def create_city_event(
    body: CityEventIn,
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    _ = load_principal_user(db, admin_user)
    if body.end_ts <= body.start_ts:
        raise HTTPException(status_code=400, detail="end_ts_must_be_after_start_ts")
    h3_center = None
    if body.center_lat is not None and body.center_lng is not None:
        h3_center = lat_lng_to_cell(body.center_lat, body.center_lng)
    row = CityEvent(
        name=body.name,
        event_type=body.event_type,
        start_ts=body.start_ts.replace(tzinfo=None) if body.start_ts.tzinfo else body.start_ts,
        end_ts=body.end_ts.replace(tzinfo=None) if body.end_ts.tzinfo else body.end_ts,
        h3_center=h3_center,
        center_lat=body.center_lat,
        center_lng=body.center_lng,
        radius_m=body.radius_m,
        confidence=body.confidence,
        notes=body.notes,
        created_at=utc_now_naive(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "event_id": row.event_id,
        "name": row.name,
        "event_type": row.event_type,
        "h3_center": row.h3_center,
        "start_ts": row.start_ts.isoformat() if row.start_ts else None,
        "end_ts": row.end_ts.isoformat() if row.end_ts else None,
    }
