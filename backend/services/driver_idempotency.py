"""Driver ride-write idempotency (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_03)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.driver_idempotency_replay import DriverIdempotencyReplay
from services.datetime_utils import utc_now_naive

T = TypeVar("T", bound=BaseModel)


def begin_or_replay(
    db: Session,
    driver_id: int,
    endpoint: str,
    idempotency_key: str | None,
    ride_id: int | None = None,
    action: str | None = None,
) -> tuple[str, DriverIdempotencyReplay | None]:
    """
    Returns (mode, row):
      no_key      — proceed without replay row
      proceed     — created in_progress row; caller runs handler then commit_result
      replay      — row has completed response to return
      in_progress — concurrent duplicate; caller should 409
    """
    if not idempotency_key:
        return ("no_key", None)

    existing = (
        db.query(DriverIdempotencyReplay)
        .filter(
            DriverIdempotencyReplay.driver_id == int(driver_id),
            DriverIdempotencyReplay.endpoint == endpoint,
            DriverIdempotencyReplay.idempotency_key == idempotency_key,
        )
        .one_or_none()
    )
    if existing and existing.state == "completed":
        return ("replay", existing)
    if existing and existing.state == "in_progress":
        return ("in_progress", None)

    row = DriverIdempotencyReplay(
        driver_id=int(driver_id),
        endpoint=endpoint,
        idempotency_key=idempotency_key,
        ride_id=ride_id,
        action=action,
        state="in_progress",
    )
    try:
        db.add(row)
        db.flush()
        return ("proceed", row)
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(DriverIdempotencyReplay)
            .filter(
                DriverIdempotencyReplay.driver_id == int(driver_id),
                DriverIdempotencyReplay.endpoint == endpoint,
                DriverIdempotencyReplay.idempotency_key == idempotency_key,
            )
            .one_or_none()
        )
        if existing and existing.state == "completed":
            return ("replay", existing)
        return ("in_progress", None)


def commit_result(db: Session, row: DriverIdempotencyReplay, status_code: int, payload: dict) -> None:
    row.status_code = int(status_code)
    row.response_json = json.dumps(payload, separators=(",", ":"), default=str)
    row.state = "completed"
    row.completed_at = utc_now_naive()
    db.flush()


def replay_response(row: DriverIdempotencyReplay) -> tuple[int, dict]:
    status = int(row.status_code or 200)
    payload = json.loads(row.response_json) if row.response_json else {}
    return status, payload


def abandon_in_progress(db: Session, row: DriverIdempotencyReplay | None) -> None:
    if row is None or row.id is None:
        return
    db.query(DriverIdempotencyReplay).filter(DriverIdempotencyReplay.id == row.id).delete()
    db.flush()


def _normalize_key(request: Request) -> str | None:
    raw = request.headers.get("Idempotency-Key")
    if not raw:
        return None
    cleaned = raw.strip()
    return cleaned[:128] if cleaned else None


def _result_to_payload(result: Any) -> dict:
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, dict):
        return result
    raise TypeError("idempotent ride write handler must return a Pydantic model or dict")


def execute_idempotent_ride_write(
    request: Request,
    db: Session,
    driver_id: int,
    endpoint: str,
    action: str,
    ride_id: int,
    handler: Callable[[], Any],
    response_model: type[T],
) -> T:
    key = _normalize_key(request)
    mode, row = begin_or_replay(db, driver_id, endpoint, key, ride_id=ride_id, action=action)

    if mode == "replay":
        assert row is not None
        status, payload = replay_response(row)
        if status != 200:
            raise HTTPException(status_code=status, detail=payload)
        return response_model.model_validate(payload)

    if mode == "in_progress":
        raise HTTPException(status_code=409, detail="idempotency_in_progress")

    try:
        result = handler()
        if row is not None:
            commit_result(db, row, 200, _result_to_payload(result))
            db.commit()
        return result
    except HTTPException:
        if row is not None:
            abandon_in_progress(db, row)
            db.commit()
        raise
    except Exception:
        if row is not None:
            abandon_in_progress(db, row)
            db.commit()
        raise
