"""Driver route quote with method + honesty flags (SIL v0.1)."""

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class RouteQuote(Base):
    __tablename__ = "route_quotes"

    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, nullable=False, index=True)
    from_h3 = Column(String(32), nullable=True)
    to_h3 = Column(String(32), nullable=True)
    route_method = Column(String(64), nullable=False)
    distance_m_est = Column(Float, nullable=True)
    duration_s_est = Column(Integer, nullable=True)
    geometry_json = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    honesty_flags_json = Column(Text, nullable=True)
    proof_receipt_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive, index=True)
