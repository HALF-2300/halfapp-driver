"""Idempotent replay records for driver ride-write POSTs (Slice 03)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class DriverIdempotencyReplay(Base):
    __tablename__ = "driver_idempotency_replays"

    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    idempotency_key = Column(String(128), nullable=False)
    endpoint = Column(String(96), nullable=False)
    ride_id = Column(Integer, nullable=True)
    action = Column(String(32), nullable=True)
    status_code = Column(Integer, nullable=True)
    response_json = Column(Text, nullable=True)
    state = Column(String(16), nullable=False, default="in_progress")
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
    completed_at = Column(DateTime, nullable=True)
