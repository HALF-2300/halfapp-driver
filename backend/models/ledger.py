from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class MarketplaceLedgerEntry(Base):
    __tablename__ = "marketplace_ledger"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('claim_attempted', 'claim_won', 'claim_lost', 'claim_released')",
            name="ck_marketplace_ledger_event_type",
        ),
        CheckConstraint("ride_id IS NOT NULL OR event_type = 'claim_attempted'", name="ck_marketplace_ledger_ride_presence"),
    )

    id = Column(Integer, primary_key=True)
    occurred_at = Column(DateTime, default=utc_now_naive, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    ride_id = Column(Integer, ForeignKey("rides.id"), index=True, nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    outcome = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    payload_json = Column(Text, default="{}", nullable=False)
    prior_hash = Column(String, nullable=True)
    entry_hash = Column(String, unique=True, nullable=False)
    policy_version = Column(String, nullable=True)


class MarketplaceLedgerEvent(Base):
    __tablename__ = "marketplace_ledger_events"
    __table_args__ = (
        Index("ix_marketplace_ledger_events_entity", "entity_type", "entity_id"),
    )

    id = Column(Integer, primary_key=True)
    occurred_at = Column(DateTime, default=utc_now_naive, index=True, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=True)
    ride_id = Column(Integer, ForeignKey("rides.id"), index=True, nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    source = Column(String, default="halfapp.backend", nullable=False)
    idempotency_key = Column(String, unique=True, nullable=True)
    correlation_id = Column(String, index=True, nullable=True)
    payload_json = Column(Text, default="{}", nullable=False)
    previous_event_hash = Column(String, nullable=True)
    event_hash = Column(String, unique=True, nullable=False)
    policy_version = Column(String, nullable=True)
