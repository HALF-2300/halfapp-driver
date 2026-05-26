"""Read-path helpers for precomputed CRL snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from models.crl_cell_snapshot import CrlCellSnapshot
from services.crl_compute import align_bucket_start as crl_align_bucket_start
from services.crl_compute import compute_crl_bucket
from services.datetime_utils import utc_now_naive

CrlSource = Literal["snapshot", "live"]


def current_bucket_has_snapshot(db: Session, *, bucket_start: datetime) -> bool:
    return (
        db.query(CrlCellSnapshot.id)
        .filter(CrlCellSnapshot.bucket_start_ts == bucket_start)
        .limit(1)
        .first()
        is not None
    )


def resolve_crl_bucket(
    db: Session,
    *,
    bucket_minutes: int = 5,
    window_minutes: int = 30,
) -> tuple[datetime, CrlSource]:
    bucket_start = crl_align_bucket_start(utc_now_naive(), bucket_minutes)
    if current_bucket_has_snapshot(db, bucket_start=bucket_start):
        return bucket_start, "snapshot"
    compute_crl_bucket(db, window_minutes=window_minutes, bucket_minutes=bucket_minutes)
    return bucket_start, "live"
