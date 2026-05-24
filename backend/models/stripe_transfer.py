"""Stripe Connect transfer records (HALFAPP_PAYMENTS_EXECUTION_05)."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint

from database import Base
from services.datetime_utils import utc_now_naive


class StripeTransfer(Base):
    __tablename__ = "stripe_transfers"
    __table_args__ = (UniqueConstraint("transfer_id", name="uq_stripe_transfers_transfer_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    transfer_id = Column(String(64), nullable=False, unique=True, index=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(8), nullable=False, default="usd")
    destination_account_id = Column(String(64), nullable=True, index=True)
    source_transaction = Column(String(64), nullable=True)
    reversed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=True)
    payment_execution_id = Column(Integer, nullable=True, index=True)
    ingested_at = Column(DateTime, nullable=False, default=utc_now_naive)
