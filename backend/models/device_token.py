"""Device token registry for future push transport (HALFAPP_PUSH_DEVICE_TOKEN_FOUNDATION_01)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func

from database import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    __table_args__ = (
        UniqueConstraint(
            "actor_type",
            "actor_id",
            "provider",
            "platform",
            "token_hash",
            name="uq_device_tokens_actor_provider_platform_hash",
        ),
    )

    id = Column(Integer, primary_key=True)
    actor_type = Column(String(32), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(16), nullable=False)
    provider = Column(String(32), nullable=False)
    token_hash = Column(String(128), nullable=False, index=True)
    token_preview = Column(String(32), nullable=False)
    device_label = Column(String(128), nullable=True)
    app_version = Column(String(64), nullable=True)
    device_model = Column(String(128), nullable=True)
    status = Column(String(16), nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
