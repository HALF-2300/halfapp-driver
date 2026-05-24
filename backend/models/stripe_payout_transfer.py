"""Links Stripe payouts to included transfers (HALFAPP_PAYMENTS_EXECUTION_05)."""

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from database import Base
from services.datetime_utils import utc_now_naive


class StripePayoutTransfer(Base):
    __tablename__ = "stripe_payout_transfers"
    __table_args__ = (
        UniqueConstraint("payout_id", "transfer_id", name="uq_payout_transfer_pair"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    payout_id = Column(String(64), nullable=False, index=True)
    transfer_id = Column(String(64), nullable=False, index=True)
    stripe_account_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
