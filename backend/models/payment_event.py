"""Stripe webhook event deduplication (HALFAPP_PAYMENTS_EXECUTION_02_5)."""

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from database import Base
from services.datetime_utils import utc_now_naive


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("external_event_id", name="uq_payment_events_external_event_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_event_id = Column(String(128), nullable=False, unique=True, index=True)
    event_type = Column(String(128), nullable=False)
    payment_execution_id = Column(Integer, nullable=True)
    processed_at = Column(DateTime, nullable=False, default=utc_now_naive)
