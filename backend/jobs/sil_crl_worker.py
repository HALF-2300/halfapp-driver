"""Background SIL (60s) and CRL (5m) snapshot recompute."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from services.crl_compute import compute_crl_bucket
from services.sil_compute import compute_sil_bucket

logger = logging.getLogger(__name__)

SIL_INTERVAL_SECONDS = 60
CRL_INTERVAL_SECONDS = 300


def run_sil_recompute_once(db: Session) -> datetime:
    """Populate ``sil_cell_aggregate`` for the current bucket."""
    return compute_sil_bucket(db)


def run_crl_recompute_once(db: Session) -> datetime:
    """Populate ``crl_cell_snapshot`` and ``crl_cell_explanation`` for the current bucket."""
    return compute_crl_bucket(db)


async def sil_crl_worker_loop(
    session_factory,
    *,
    sil_interval_seconds: int = SIL_INTERVAL_SECONDS,
    crl_interval_seconds: int = CRL_INTERVAL_SECONDS,
) -> None:
    """Run SIL every 60s and CRL every 5m until cancelled."""
    sil_elapsed = sil_interval_seconds
    crl_elapsed = crl_interval_seconds
    tick = 5

    while True:
        await asyncio.sleep(tick)
        sil_elapsed += tick
        crl_elapsed += tick

        if sil_elapsed >= sil_interval_seconds:
            sil_elapsed = 0
            db = session_factory()
            try:
                bucket = run_sil_recompute_once(db)
                logger.info("sil_crl_worker sil bucket=%s", bucket.isoformat())
            except Exception:
                logger.exception("sil_crl_worker sil recompute failed")
                db.rollback()
            finally:
                db.close()

        if crl_elapsed >= crl_interval_seconds:
            crl_elapsed = 0
            db = session_factory()
            try:
                bucket = run_crl_recompute_once(db)
                logger.info("sil_crl_worker crl bucket=%s", bucket.isoformat())
            except Exception:
                logger.exception("sil_crl_worker crl recompute failed")
                db.rollback()
            finally:
                db.close()
