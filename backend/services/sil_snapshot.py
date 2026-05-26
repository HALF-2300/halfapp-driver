"""Read-path helpers for precomputed SIL aggregates."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from models.sil_cell_aggregate import SilCellAggregate
from services.datetime_utils import utc_now_naive
from services.sil_compute import align_bucket_start, compute_sil_bucket

SilSource = Literal["snapshot", "live"]


def current_bucket_has_snapshot(db: Session, *, bucket_start: datetime) -> bool:
    return (
        db.query(SilCellAggregate.id)
        .filter(SilCellAggregate.bucket_start_ts == bucket_start)
        .limit(1)
        .first()
        is not None
    )


def resolve_sil_bucket(
    db: Session,
    *,
    bucket_minutes: int = 5,
    window_minutes: int = 30,
) -> tuple[datetime, SilSource]:
    """Return bucket start and whether rows came from cache or live recompute."""
    bucket_start = align_bucket_start(utc_now_naive(), bucket_minutes)
    if current_bucket_has_snapshot(db, bucket_start=bucket_start):
        return bucket_start, "snapshot"
    compute_sil_bucket(db, window_minutes=window_minutes, bucket_minutes=bucket_minutes)
    return bucket_start, "live"
