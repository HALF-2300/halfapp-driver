"""Driver-editable profile overlay (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from database import Base
from services.datetime_utils import utc_now_naive


class DriverProfile(Base):
    __tablename__ = "driver_profiles"

    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name = Column(String(64), nullable=True)
    phone_e164 = Column(String(32), nullable=True)
    photo_url = Column(String(256), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
    updated_at = Column(DateTime, nullable=False, default=utc_now_naive, onupdate=utc_now_naive)
