"""Driver Stripe Connect account mapping (HALFAPP_PAYMENTS_EXECUTION_02)."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from database import Base
from services.datetime_utils import utc_now_naive


class DriverStripeAccount(Base):
    __tablename__ = "driver_stripe_accounts"
    __table_args__ = (
        UniqueConstraint("driver_id", name="uq_driver_stripe_accounts_driver_id"),
        UniqueConstraint("stripe_account_id", name="uq_driver_stripe_accounts_stripe_account_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stripe_account_id = Column(String(64), nullable=False, unique=True, index=True)
    charges_enabled = Column(Boolean, nullable=False, default=False)
    payouts_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
