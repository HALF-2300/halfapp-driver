"""Stripe Connect account payout records (HALFAPP_PAYMENTS_EXECUTION_05)."""

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from database import Base
from services.datetime_utils import utc_now_naive


class StripePayout(Base):
    __tablename__ = "stripe_payouts"
    __table_args__ = (UniqueConstraint("payout_id", name="uq_stripe_payouts_payout_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    payout_id = Column(String(64), nullable=False, unique=True, index=True)
    stripe_account_id = Column(String(64), nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(8), nullable=False, default="usd")
    status = Column(String(32), nullable=False)
    arrival_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    ingested_at = Column(DateTime, nullable=False, default=utc_now_naive)
