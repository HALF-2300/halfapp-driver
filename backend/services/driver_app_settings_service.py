"""Driver app settings CRUD (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02)."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from models.driver_app_settings import DriverAppSettings
from services.datetime_utils import utc_now_naive

_ALLOWED_UNITS = frozenset({"mi", "km"})
_ALLOWED_THEMES = frozenset({"light", "dark", "system"})


def settings_to_dict(row: DriverAppSettings) -> dict:
    quiet = None
    if row.notif_quiet_hours_json:
        try:
            quiet = json.loads(row.notif_quiet_hours_json)
        except json.JSONDecodeError:
            quiet = None
    return {
        "units": row.units,
        "locale": row.locale,
        "theme": row.theme,
        "notif_push_enabled": bool(row.notif_push_enabled),
        "notif_sound_enabled": bool(row.notif_sound_enabled),
        "notif_quiet_hours": quiet,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_or_create_settings(db: Session, driver_id: int) -> DriverAppSettings:
    row = (
        db.query(DriverAppSettings)
        .filter(DriverAppSettings.driver_id == int(driver_id))
        .one_or_none()
    )
    if row is not None:
        return row
    row = DriverAppSettings(driver_id=int(driver_id))
    db.add(row)
    db.flush()
    return row


def update_settings(db: Session, driver_id: int, data: dict) -> DriverAppSettings:
    row = get_or_create_settings(db, driver_id)

    if "units" in data and data["units"] is not None:
        units = str(data["units"]).strip().lower()
        if units not in _ALLOWED_UNITS:
            raise ValueError("invalid_units")
        row.units = units

    if "locale" in data and data["locale"] is not None:
        row.locale = str(data["locale"]).strip()[:16] or "en-US"

    if "theme" in data and data["theme"] is not None:
        theme = str(data["theme"]).strip().lower()
        if theme not in _ALLOWED_THEMES:
            raise ValueError("invalid_theme")
        row.theme = theme

    if "notif_push_enabled" in data and data["notif_push_enabled"] is not None:
        row.notif_push_enabled = bool(data["notif_push_enabled"])

    if "notif_sound_enabled" in data and data["notif_sound_enabled"] is not None:
        row.notif_sound_enabled = bool(data["notif_sound_enabled"])

    if "notif_quiet_hours" in data:
        qh = data["notif_quiet_hours"]
        row.notif_quiet_hours_json = json.dumps(qh) if qh is not None else None

    row.updated_at = utc_now_naive()
    db.flush()
    return row
