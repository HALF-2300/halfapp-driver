"""City Reality Layer — driver-facing v0.1 API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from services.crl_map import build_crl_explain_response, build_crl_map_response
from services.rbac import AuthPrincipal, require_role

router = APIRouter(prefix="/v1/crl", tags=["city-reality"])
DRIVER_ACCESS = require_role("driver")


@router.get("/map")
def crl_map(
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
    window: str = Query(default="30m"),
    min_conf: float = Query(default=0.4, ge=0.0, le=1.0),
):
    _ = driver_user
    window_minutes = 30
    if window.endswith("m"):
        try:
            window_minutes = int(window[:-1])
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid_window") from None
    return build_crl_map_response(db, window_minutes=window_minutes, min_conf=min_conf)


@router.get("/explain")
def crl_explain(
    h3: str = Query(..., min_length=3),
    driver_user: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    _ = driver_user
    body = build_crl_explain_response(db, h3_cell=h3)
    if body is None:
        raise HTTPException(status_code=404, detail="cell_not_found")
    return body
