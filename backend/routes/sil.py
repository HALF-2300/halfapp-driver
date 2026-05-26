"""Street Intelligence Layer — driver-facing v0.1 API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database import get_db
from services.rbac import AuthPrincipal, require_role
from services.route_quote_service import create_route_quote, get_proof_receipt_summary
from services.sil_h3 import lat_lng_to_cell
from services.sil_map import build_sil_map_response, build_sil_suggest_response

router = APIRouter(prefix="/v1/sil", tags=["street-intelligence"])
DRIVER_ACCESS = require_role("driver")


class RouteQuoteIn(BaseModel):
    from_lat: float
    from_lng: float
    to_lat: float
    to_lng: float
    mode: str = "driving"

    @field_validator("from_lat", "to_lat")
    @classmethod
    def lat_range(cls, v: float) -> float:
        if v < -90 or v > 90:
            raise ValueError("lat out of range")
        return v

    @field_validator("from_lng", "to_lng")
    @classmethod
    def lng_range(cls, v: float) -> float:
        if v < -180 or v > 180:
            raise ValueError("lng out of range")
        return v


@router.get("/map")
def sil_map(
    response: Response,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    bbox: str | None = None,
    h3_res: int = Query(default=7, ge=5, le=9),
    window: str = Query(default="30m"),
    layers: str = Query(default="busy,slow"),
    min_conf: float = Query(default=0.4, ge=0.0, le=1.0),
):
    _ = driver_user
    _ = h3_res
    window_minutes = 30
    if window.endswith("m"):
        try:
            window_minutes = int(window[:-1])
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid_window") from None
    body, source = build_sil_map_response(
        db,
        bbox=bbox,
        window_minutes=window_minutes,
        layers=layers,
        min_conf=min_conf,
    )
    response.headers["X-SIL-Source"] = source
    return body


@router.get("/suggest")
def sil_suggest(
    response: Response,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    driver_h3: str | None = None,
    driver_lat: float | None = None,
    driver_lng: float | None = None,
    horizon: str = Query(default="15m"),
):
    _ = driver_user
    if driver_h3:
        cell = driver_h3
    elif driver_lat is not None and driver_lng is not None:
        cell = lat_lng_to_cell(driver_lat, driver_lng)
    else:
        raise HTTPException(status_code=400, detail="driver_h3_or_lat_lng_required")

    horizon_minutes = 15
    if horizon.endswith("m"):
        try:
            horizon_minutes = int(horizon[:-1])
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid_horizon") from None

    body, source = build_sil_suggest_response(db, driver_h3=cell, horizon_minutes=horizon_minutes)
    response.headers["X-SIL-Source"] = source
    return body


@router.post("/route/quote")
def sil_route_quote(
    body: RouteQuoteIn,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    from services.rbac import load_principal_user

    driver_user = load_principal_user(db, driver_user)
    return create_route_quote(
        db,
        driver_id=driver_user.id,
        from_lat=body.from_lat,
        from_lng=body.from_lng,
        to_lat=body.to_lat,
        to_lng=body.to_lng,
    )


@router.get("/proof/receipt/{receipt_id}")
def sil_proof_receipt(
    receipt_id: int,
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    _ = driver_user
    summary = get_proof_receipt_summary(db, receipt_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="receipt_not_found")
    return summary
