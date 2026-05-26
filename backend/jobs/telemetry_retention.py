"""Delete fleet telemetry points older than the configured retention window."""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from models.driver_telemetry_point import DriverTelemetryPoint
from services.datetime_utils import utc_now_naive
from services.fleet_traffic_heatmap import build_fleet_traffic_heatmap
from services.telemetry_config import get_telemetry_retention_days

logger = logging.getLogger(__name__)


def run_telemetry_retention_once(db: Session) -> int:
    """
    Remove points older than ``HALFAPP_TELEMETRY_RETENTION_DAYS``.

    Heatmap overlays are computed on read from recent points; no separate
    aggregate table is updated before delete.
    """
    days = get_telemetry_retention_days()
    cutoff = utc_now_naive() - timedelta(days=days)
    # Touch heatmap path so retention runs after the same code path drivers use.
    build_fleet_traffic_heatmap(db, minutes=min(days * 24 * 60, 120))

    deleted = (
        db.query(DriverTelemetryPoint)
        .filter(DriverTelemetryPoint.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    if deleted:
        logger.info(
            "telemetry_retention deleted=%s cutoff=%s retention_days=%s",
            deleted,
            cutoff.isoformat(),
            days,
        )
    return int(deleted or 0)
