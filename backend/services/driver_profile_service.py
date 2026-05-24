"""Driver profile overlay CRUD (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.driver_profile import DriverProfile
from services.datetime_utils import utc_now_naive


def profile_to_dict(row: DriverProfile) -> dict:
    return {
        "display_name": row.display_name,
        "phone_e164": row.phone_e164,
        "photo_url": row.photo_url,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_or_create_profile(db: Session, driver_id: int) -> DriverProfile:
    row = db.query(DriverProfile).filter(DriverProfile.driver_id == int(driver_id)).one_or_none()
    if row is not None:
        return row
    row = DriverProfile(driver_id=int(driver_id))
    db.add(row)
    db.flush()
    return row


def update_profile(db: Session, driver_id: int, data: dict) -> DriverProfile:
    row = get_or_create_profile(db, driver_id)
    for key in ("display_name", "phone_e164", "photo_url"):
        if key in data:
            value = data[key]
            if value is not None and isinstance(value, str):
                value = value.strip() or None
            setattr(row, key, value)
    row.updated_at = utc_now_naive()
    db.flush()
    return row
