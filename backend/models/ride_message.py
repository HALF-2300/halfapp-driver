"""Per-ride messages (driver ↔ rider storage; delivery to rider is out of band)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class RideMessage(Base):
    __tablename__ = "ride_messages"

    id = Column(Integer, primary_key=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_role = Column(String(16), nullable=False)
    sender_id = Column(Integer, nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
    read_by_driver_at = Column(DateTime, nullable=True)
