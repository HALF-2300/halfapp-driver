"""Driver app preferences (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02)."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class DriverAppSettings(Base):
    __tablename__ = "driver_settings"

    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    units = Column(String(8), nullable=False, default="mi")
    locale = Column(String(16), nullable=False, default="en-US")
    theme = Column(String(16), nullable=False, default="system")
    notif_push_enabled = Column(Boolean, nullable=False, default=False)
    notif_sound_enabled = Column(Boolean, nullable=False, default=True)
    notif_quiet_hours_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
    updated_at = Column(DateTime, nullable=False, default=utc_now_naive, onupdate=utc_now_naive)
