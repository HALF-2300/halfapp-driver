"""Support cases — recorded help/lost-item reports (HALFAPP_SUPPORT_HELP_LOST_ITEM_CONTRACT_01)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.types import JSON

from database import Base


class SupportCase(Base):
    __tablename__ = "support_cases"

    id = Column(Integer, primary_key=True)
    case_uid = Column(String(32), nullable=False, unique=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_type = Column(String(32), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="open", index=True)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    contact_preference = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    closed_at = Column(DateTime(timezone=True), nullable=True)
