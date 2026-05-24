"""Sequential dispatch attempt log (RIDE-003)."""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from database import Base
from services.datetime_utils import utc_now_naive

DISPATCH_RESULT_SENT = "sent"
DISPATCH_RESULT_ACCEPTED = "accepted"
DISPATCH_RESULT_DECLINED = "declined"
DISPATCH_RESULT_TIMEOUT = "timeout"
DISPATCH_RESULT_SKIPPED_INELIGIBLE = "skipped_ineligible"
# Legacy alias — open attempts use ``sent`` (RIDE-003 contract).
DISPATCH_RESULT_PENDING = DISPATCH_RESULT_SENT


class RideDispatchLog(Base):
    __tablename__ = "ride_dispatch_log"

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sent_at = Column(DateTime, default=utc_now_naive, nullable=False)
    result = Column(String(32), default=DISPATCH_RESULT_SENT, nullable=False)
    responded_at = Column(DateTime, nullable=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive, nullable=False)
