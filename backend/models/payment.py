"""Product payment record — Phase 3 simulated money loop (not Stripe)."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base
from services.datetime_utils import utc_now_naive

PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_AUTHORIZED = "authorized"
PAYMENT_STATUS_CAPTURED = "captured"
PAYMENT_STATUS_FAILED = "failed"

PAYMENT_STATUSES = frozenset(
    {
        PAYMENT_STATUS_PENDING,
        PAYMENT_STATUS_AUTHORIZED,
        PAYMENT_STATUS_CAPTURED,
        PAYMENT_STATUS_FAILED,
    }
)


class RidePayment(Base):
    """One payment row per ride — pending → authorized → captured."""

    __tablename__ = "ride_payments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'authorized', 'captured', 'failed')",
            name="ck_ride_payments_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    rider_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    amount_cents = Column(Integer, nullable=False, default=0)
    driver_payout_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(32), nullable=False, default=PAYMENT_STATUS_PENDING)
    created_at = Column(DateTime, default=utc_now_naive, nullable=False)
    authorized_at = Column(DateTime, nullable=True)
    captured_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

    ride = relationship("Ride", foreign_keys=[ride_id], backref="payment_record")
