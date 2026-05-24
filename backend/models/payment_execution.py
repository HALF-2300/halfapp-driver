"""Payment execution attempts — separate from ride_pricing truth (HALFAPP_PAYMENTS_EXECUTION_01)."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from database import Base
from services.datetime_utils import utc_now_naive

EXECUTION_TYPE_CHARGE_RIDER = "charge_rider"
EXECUTION_TYPE_REFUND_RIDER = "refund_rider"
EXECUTION_TYPE_DISPUTE = "dispute"
EXECUTION_TYPE_PAYOUT_DRIVER = "payout_driver"

STATUS_PENDING = "pending"
STATUS_REQUIRES_ACTION = "requires_action"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_CANCELED = "canceled"
STATUS_REQUIRES_DRIVER_CONNECT = "requires_driver_connect"

EXTERNAL_PROVIDER_STRIPE = "stripe"


class PaymentExecution(Base):
    __tablename__ = "payment_execution"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_payment_execution_idempotency"),
        Index("ix_payment_execution_ride_type", "ride_id", "execution_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), nullable=False, index=True)
    ride_pricing_id = Column(
        Integer,
        ForeignKey("ride_pricing.ride_id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_type = Column(String(32), nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(8), nullable=False, default="usd")
    external_provider = Column(String(32), nullable=True)
    external_id = Column(String(128), nullable=True, unique=True)
    external_charge_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), nullable=False, index=True)
    idempotency_key = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
    updated_at = Column(DateTime, nullable=True, onupdate=utc_now_naive)
    is_test = Column(Boolean, nullable=False, default=False)
