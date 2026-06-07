"""Delivery orders foundation.

Revision ID: 0041_delivery_orders_foundation
Revises: 0040_support_cases_foundation
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0041_delivery_orders_foundation"
down_revision = "0040_support_cases_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("courier_id", sa.Integer(), nullable=True),
        sa.Column("merchant_operator_id", sa.Integer(), nullable=True),
        sa.Column("merchant_name", sa.String(length=160), nullable=False),
        sa.Column("merchant_access_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("pickup_address", sa.String(length=255), nullable=False),
        sa.Column("dropoff_address", sa.String(length=255), nullable=False),
        sa.Column("items_summary", sa.Text(), nullable=True),
        sa.Column("delivery_notes", sa.Text(), nullable=True),
        sa.Column("pickup_latitude", sa.Float(), nullable=True),
        sa.Column("pickup_longitude", sa.Float(), nullable=True),
        sa.Column("dropoff_latitude", sa.Float(), nullable=True),
        sa.Column("dropoff_longitude", sa.Float(), nullable=True),
        sa.Column("distance_km", sa.Float(), nullable=False, server_default="0"),
        sa.Column("scheduled_for", sa.DateTime(), nullable=True),
        sa.Column("contactless", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("items_subtotal_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivery_fee_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("service_fee_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("small_order_fee_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tax_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tip_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("customer_charge_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("platform_fee_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("courier_payout_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("merchant_payout_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("refunded_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pricing_version", sa.String(length=32), nullable=True),
        sa.Column("payment_provider", sa.String(length=32), nullable=True),
        sa.Column("payment_reference", sa.String(length=128), nullable=True),
        sa.Column("masked_contact_channel", sa.String(length=64), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("support_case_id", sa.Integer(), nullable=True),
        sa.Column("evidence_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("priced_at", sa.DateTime(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("merchant_accepted_at", sa.DateTime(), nullable=True),
        sa.Column("preparing_at", sa.DateTime(), nullable=True),
        sa.Column("ready_for_pickup_at", sa.DateTime(), nullable=True),
        sa.Column("courier_assigned_at", sa.DateTime(), nullable=True),
        sa.Column("picked_up_at", sa.DateTime(), nullable=True),
        sa.Column("en_route_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("refunded_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('created', 'priced', 'paid', 'merchant_accepted', 'preparing', "
            "'ready_for_pickup', 'courier_assigned', 'picked_up', 'en_route', "
            "'delivered', 'cancelled', 'refunded', 'failed')",
            name="ck_delivery_orders_status_known",
        ),
        sa.CheckConstraint("customer_charge_cents >= 0", name="ck_delivery_customer_charge_nonneg"),
        sa.CheckConstraint("platform_fee_cents >= 0", name="ck_delivery_platform_fee_nonneg"),
        sa.CheckConstraint("courier_payout_cents >= 0", name="ck_delivery_courier_payout_nonneg"),
        sa.CheckConstraint("merchant_payout_cents >= 0", name="ck_delivery_merchant_payout_nonneg"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["courier_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["merchant_operator_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["support_case_id"], ["support_cases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delivery_orders_status", "delivery_orders", ["status"])
    op.create_index("ix_delivery_orders_customer_id", "delivery_orders", ["customer_id"])
    op.create_index("ix_delivery_orders_courier_id", "delivery_orders", ["courier_id"])
    op.create_index("ix_delivery_orders_merchant_operator_id", "delivery_orders", ["merchant_operator_id"])
    op.create_index("ix_delivery_orders_merchant_access_code", "delivery_orders", ["merchant_access_code"])
    op.create_index("ix_delivery_orders_status_courier", "delivery_orders", ["status", "courier_id"])
    op.create_index("ix_delivery_orders_status_merchant", "delivery_orders", ["status", "merchant_operator_id"])

    op.create_table(
        "delivery_settlement_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("party", sa.String(length=32), nullable=False),
        sa.Column("entry_type", sa.String(length=48), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ready"),
        sa.Column("evidence_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("amount_cents >= 0", name="ck_delivery_settlement_amount_nonneg"),
        sa.CheckConstraint(
            "party IN ('customer', 'merchant', 'courier', 'platform', 'tax_authority')",
            name="ck_delivery_settlement_party_known",
        ),
        sa.CheckConstraint(
            "entry_type IN ('customer_charge', 'merchant_payout', 'courier_payout', "
            "'platform_fee', 'tax_liability', 'refund')",
            name="ck_delivery_settlement_type_known",
        ),
        sa.ForeignKeyConstraint(["order_id"], ["delivery_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delivery_settlement_entries_order_id", "delivery_settlement_entries", ["order_id"])
    op.create_index("ix_delivery_settlement_entries_party", "delivery_settlement_entries", ["party"])
    op.create_index("ix_delivery_settlement_entries_entry_type", "delivery_settlement_entries", ["entry_type"])


def downgrade() -> None:
    op.drop_index("ix_delivery_settlement_entries_entry_type", table_name="delivery_settlement_entries")
    op.drop_index("ix_delivery_settlement_entries_party", table_name="delivery_settlement_entries")
    op.drop_index("ix_delivery_settlement_entries_order_id", table_name="delivery_settlement_entries")
    op.drop_table("delivery_settlement_entries")
    op.drop_index("ix_delivery_orders_status_merchant", table_name="delivery_orders")
    op.drop_index("ix_delivery_orders_status_courier", table_name="delivery_orders")
    op.drop_index("ix_delivery_orders_merchant_access_code", table_name="delivery_orders")
    op.drop_index("ix_delivery_orders_merchant_operator_id", table_name="delivery_orders")
    op.drop_index("ix_delivery_orders_courier_id", table_name="delivery_orders")
    op.drop_index("ix_delivery_orders_customer_id", table_name="delivery_orders")
    op.drop_index("ix_delivery_orders_status", table_name="delivery_orders")
    op.drop_table("delivery_orders")
