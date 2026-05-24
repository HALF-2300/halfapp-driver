from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from database import Base
from services.datetime_utils import utc_now_naive

SETTLEMENT_STATUS_PENDING = "pending"
SETTLEMENT_STATUS_READY = "ready"
SETTLEMENT_STATUS_MANUALLY_MARKED_PAID = "manually_marked_paid"
SETTLEMENT_STATUS_CANCELLED = "cancelled"
SETTLEMENT_STATUS_DISPUTED_PLACEHOLDER = "disputed_placeholder"

ALLOWED_SETTLEMENT_STATUSES = frozenset(
    {
        SETTLEMENT_STATUS_PENDING,
        SETTLEMENT_STATUS_READY,
        SETTLEMENT_STATUS_MANUALLY_MARKED_PAID,
        SETTLEMENT_STATUS_CANCELLED,
        SETTLEMENT_STATUS_DISPUTED_PLACEHOLDER,
    }
)

ENTRY_TYPE_CUSTOMER_CHARGE = "customer_charge_obligation"
ENTRY_TYPE_DRIVER_PAYOUT = "driver_payout_obligation"
ENTRY_TYPE_PLATFORM_COMMISSION = "platform_commission"
ENTRY_TYPE_PLATFORM_SERVICE_FEE = "platform_service_fee"
ENTRY_TYPE_PLATFORM_REVENUE = "platform_revenue"
ENTRY_TYPE_TIP_DRIVER = "tip_payable_to_driver"
ENTRY_TYPE_CITY_LIABILITY = "city_fee_liability"
ENTRY_TYPE_AIRPORT_LIABILITY = "airport_fee_liability"
ENTRY_TYPE_TOLL_LIABILITY = "toll_liability"
ENTRY_TYPE_ACCESSIBILITY_LIABILITY = "accessibility_fee_liability"
ENTRY_TYPE_TAX_LIABILITY = "tax_liability"

ALLOWED_ENTRY_TYPES = frozenset(
    {
        ENTRY_TYPE_CUSTOMER_CHARGE,
        ENTRY_TYPE_DRIVER_PAYOUT,
        ENTRY_TYPE_PLATFORM_COMMISSION,
        ENTRY_TYPE_PLATFORM_SERVICE_FEE,
        ENTRY_TYPE_PLATFORM_REVENUE,
        ENTRY_TYPE_TIP_DRIVER,
        ENTRY_TYPE_CITY_LIABILITY,
        ENTRY_TYPE_AIRPORT_LIABILITY,
        ENTRY_TYPE_TOLL_LIABILITY,
        ENTRY_TYPE_ACCESSIBILITY_LIABILITY,
        ENTRY_TYPE_TAX_LIABILITY,
    }
)

PARTY_RIDER = "rider"
PARTY_DRIVER = "driver"
PARTY_PLATFORM = "platform"
PARTY_CITY = "city"
PARTY_AIRPORT = "airport"
PARTY_TOLL_AUTHORITY = "toll_authority"
PARTY_TAX_AUTHORITY = "tax_authority"

SOURCE_RIDE_PRICING_LOCKED = "ride_pricing_locked"


class SettlementEntry(Base):
    __tablename__ = "settlement_entries"
    __table_args__ = (
        UniqueConstraint("ride_id", "entry_type", name="uq_settlement_entries_ride_entry_type"),
        CheckConstraint(
            "settlement_status IN ('pending', 'ready', 'manually_marked_paid', 'cancelled', 'disputed_placeholder')",
            name="ck_settlement_entries_status_known",
        ),
        CheckConstraint("amount_cents >= 0", name="ck_settlement_entries_amount_nonneg"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), nullable=False, index=True)
    pricing_id = Column(Integer, ForeignKey("ride_pricing.ride_id", ondelete="CASCADE"), nullable=False)
    route_snapshot_id = Column(Integer, ForeignKey("route_snapshots.id", ondelete="SET NULL"), nullable=True)
    settlement_status = Column(String, nullable=False, default=SETTLEMENT_STATUS_READY)
    entry_type = Column(String, nullable=False)
    party = Column(String, nullable=False)
    amount_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String, nullable=False, default="USD")
    source = Column(String, nullable=False, default=SOURCE_RIDE_PRICING_LOCKED)
    entry_checksum = Column(String, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive, nullable=False)
    locked_at = Column(DateTime, default=utc_now_naive, nullable=False)
