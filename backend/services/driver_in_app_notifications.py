"""In-app driver notifications (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_04). No push delivery."""

from __future__ import annotations

import os
from datetime import timedelta

from sqlalchemy.orm import Session

from services.datetime_utils import utc_now_naive
from services.lifecycle import NotificationType


def inapp_notifications_enabled() -> bool:
    return os.getenv("INAPP_NOTIFICATIONS_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def notify_driver_in_app(
    db: Session,
    *,
    driver_id: int,
    title: str,
    message: str,
    notif_type: str | NotificationType = NotificationType.SYSTEM,
    expires_hours: int = 72,
) -> None:
    """Insert a row the driver reads via GET /notifications/."""
    if not inapp_notifications_enabled():
        return

    from routes.notifications import Notification

    type_value = notif_type.value if isinstance(notif_type, NotificationType) else str(notif_type)
    row = Notification(
        user_id=int(driver_id),
        title=title[:255] if title else "Update",
        message=message,
        type=type_value,
        is_read=False,
        expires_at=utc_now_naive() + timedelta(hours=expires_hours),
    )
    db.add(row)
    db.flush()
