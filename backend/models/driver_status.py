from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer

from database import Base
from services.datetime_utils import utc_now_naive


class DriverStatusRecord(Base):
    """Persistent driver online/offline and location freshness (DRIVER-001)."""

    __tablename__ = "driver_status"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)
    online = Column(Boolean, default=False, nullable=False)
    last_lat = Column(Float, nullable=True)
    last_lng = Column(Float, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    current_ride_id = Column(Integer, ForeignKey("rides.id"), nullable=True)
    updated_at = Column(DateTime, default=utc_now_naive, nullable=False)
