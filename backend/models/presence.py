from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class DriverPresence(Base):
    __tablename__ = "driver_presence"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)
    requested_state = Column(String, default="offline", nullable=False)
    effective_state = Column(String, default="offline", nullable=False)
    state_changed_at = Column(DateTime, default=utc_now_naive, nullable=False)
    heartbeat_at = Column(DateTime, nullable=True)
    stale_reason = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utc_now_naive, nullable=False)
