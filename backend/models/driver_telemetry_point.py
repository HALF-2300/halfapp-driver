"""GPS speed samples from online drivers (fleet traffic heat; not municipal traffic data)."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer

from database import Base
from services.datetime_utils import utc_now_naive


class DriverTelemetryPoint(Base):
    __tablename__ = "driver_telemetry_points"

    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    speed_mps = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive, index=True)
