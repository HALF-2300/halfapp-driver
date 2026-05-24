"""Driver-reported trip issues (ops review; not a full ticketing product)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class DriverSupportTicket(Base):
    __tablename__ = "driver_support_tickets"

    id = Column(Integer, primary_key=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="SET NULL"), nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(64), nullable=False, default="trip_issue")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
