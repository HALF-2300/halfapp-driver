"""Operator or inferred city events affecting demand attribution."""

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class CityEvent(Base):
    __tablename__ = "city_events"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    event_type = Column(String(64), nullable=False)
    start_ts = Column(DateTime, nullable=False)
    end_ts = Column(DateTime, nullable=False)
    h3_center = Column(String(32), nullable=True)
    center_lat = Column(Float, nullable=True)
    center_lng = Column(Float, nullable=True)
    radius_m = Column(Float, nullable=True, default=1500.0)
    confidence = Column(Float, nullable=False, default=0.8)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
