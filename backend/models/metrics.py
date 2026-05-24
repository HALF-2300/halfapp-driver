from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, index=True, nullable=False)
    value = Column(Float, nullable=False)
    ride_id = Column(Integer, ForeignKey("rides.id"), index=True, nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    timestamp = Column(DateTime, default=utc_now_naive, nullable=False)


class RideVisibility(Base):
    __tablename__ = "ride_visibility"
    __table_args__ = (
        Index("ux_ride_visibility_ride_driver", "ride_id", "driver_id", unique=True),
        Index("ix_ride_visibility_driver_dismissed", "driver_id", "dismissed_at"),
        Index("ix_ride_visibility_driver_status_expires", "driver_id", "status", "expires_at"),
        Index("ix_ride_visibility_ride_id", "ride_id"),
    )

    id = Column(Integer, primary_key=True)
    ride_id = Column(Integer, ForeignKey("rides.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    first_seen_at = Column(DateTime, default=utc_now_naive, nullable=False)
    last_seen_at = Column(DateTime, default=utc_now_naive, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String, default="visible", nullable=False)
    reason = Column(Text, nullable=True)
    policy_version = Column(String, default="ranked_open_board_v1", nullable=False)
    ordering_rank = Column(Integer, nullable=False)
    ordering_score = Column(Float, nullable=True)
    why_this_rank_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    correlation_id = Column(String, nullable=True)


class RideClaimAttempt(Base):
    __tablename__ = "ride_claim_attempts"

    id = Column(Integer, primary_key=True)
    ride_id = Column(Integer, ForeignKey("rides.id"), index=True, nullable=False)
    driver_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    attempted_at = Column(DateTime, default=utc_now_naive, nullable=False)
    outcome = Column(String, nullable=False)
    competing_driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    policy_version = Column(String, default="ranked_open_board_v1", nullable=False)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_entity", "entity_type", "entity_id"),
        Index("ix_events_occurred_at", "occurred_at"),
    )

    event_id = Column(Integer, primary_key=True)
    occurred_at = Column(DateTime, default=utc_now_naive, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    event_type = Column(String, nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    payload_json = Column(Text, nullable=True)
    policy_version = Column(String, nullable=True)
