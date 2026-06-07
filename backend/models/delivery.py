"""Delivery marketplace persistence foundation.

These tables are intentionally separate from the existing ride spine. They give
food/package delivery its own lifecycle, pricing, settlement, and evidence
records without weakening the already-tested ride state machine.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


DELIVERY_ORDER_STATUSES = (
    "created",
    "priced",
    "paid",
    "merchant_accepted",
    "preparing",
    "ready_for_pickup",
    "courier_assigned",
    "picked_up",
    "en_route",
    "delivered",
    "cancelled",
    "refunded",
    "failed",
)


class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('created', 'priced', 'paid', 'merchant_accepted', 'preparing', "
            "'ready_for_pickup', 'courier_assigned', 'picked_up', 'en_route', "
            "'delivered', 'cancelled', 'refunded', 'failed')",
            name="ck_delivery_orders_status_known",
        ),
        CheckConstraint("customer_charge_cents >= 0", name="ck_delivery_customer_charge_nonneg"),
        CheckConstraint("platform_fee_cents >= 0", name="ck_delivery_platform_fee_nonneg"),
        CheckConstraint("courier_payout_cents >= 0", name="ck_delivery_courier_payout_nonneg"),
        CheckConstraint("merchant_payout_cents >= 0", name="ck_delivery_merchant_payout_nonneg"),
    )

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    courier_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    merchant_operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    merchant_name = Column(String(160), nullable=False)
    merchant_access_code = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="created", index=True)

    pickup_address = Column(String(255), nullable=False)
    dropoff_address = Column(String(255), nullable=False)
    items_summary = Column(Text, nullable=True)
    delivery_notes = Column(Text, nullable=True)
    pickup_latitude = Column(Float, nullable=True)
    pickup_longitude = Column(Float, nullable=True)
    dropoff_latitude = Column(Float, nullable=True)
    dropoff_longitude = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=False, default=0.0)
    scheduled_for = Column(DateTime, nullable=True)
    contactless = Column(Integer, nullable=False, default=0)

    currency = Column(String(8), nullable=False, default="USD")
    items_subtotal_cents = Column(Integer, nullable=False, default=0)
    delivery_fee_cents = Column(Integer, nullable=False, default=0)
    service_fee_cents = Column(Integer, nullable=False, default=0)
    small_order_fee_cents = Column(Integer, nullable=False, default=0)
    tax_cents = Column(Integer, nullable=False, default=0)
    tip_cents = Column(Integer, nullable=False, default=0)
    customer_charge_cents = Column(Integer, nullable=False, default=0)
    platform_fee_cents = Column(Integer, nullable=False, default=0)
    courier_payout_cents = Column(Integer, nullable=False, default=0)
    merchant_payout_cents = Column(Integer, nullable=False, default=0)
    refunded_cents = Column(Integer, nullable=False, default=0)

    pricing_version = Column(String(32), nullable=True)
    payment_provider = Column(String(32), nullable=True)
    payment_reference = Column(String(128), nullable=True)
    masked_contact_channel = Column(String(64), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)
    support_case_id = Column(Integer, ForeignKey("support_cases.id", ondelete="SET NULL"), nullable=True)
    evidence_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now_naive, nullable=False)
    priced_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    merchant_accepted_at = Column(DateTime, nullable=True)
    preparing_at = Column(DateTime, nullable=True)
    ready_for_pickup_at = Column(DateTime, nullable=True)
    courier_assigned_at = Column(DateTime, nullable=True)
    picked_up_at = Column(DateTime, nullable=True)
    en_route_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive, nullable=False)


class DeliverySettlementEntry(Base):
    __tablename__ = "delivery_settlement_entries"
    __table_args__ = (
        CheckConstraint("amount_cents >= 0", name="ck_delivery_settlement_amount_nonneg"),
        CheckConstraint(
            "party IN ('customer', 'merchant', 'courier', 'platform', 'tax_authority')",
            name="ck_delivery_settlement_party_known",
        ),
        CheckConstraint(
            "entry_type IN ('customer_charge', 'merchant_payout', 'courier_payout', "
            "'platform_fee', 'tax_liability', 'refund')",
            name="ck_delivery_settlement_type_known",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("delivery_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    party = Column(String(32), nullable=False, index=True)
    entry_type = Column(String(48), nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(8), nullable=False, default="USD")
    status = Column(String(32), nullable=False, default="ready")
    evidence_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive, nullable=False)


Index("ix_delivery_orders_status_courier", DeliveryOrder.status, DeliveryOrder.courier_id)
Index("ix_delivery_orders_status_merchant", DeliveryOrder.status, DeliveryOrder.merchant_operator_id)
