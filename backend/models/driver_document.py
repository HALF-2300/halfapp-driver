"""Driver document intake records (metadata-first; ops review)."""

from __future__ import annotations

import enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from database import Base


class DriverDocumentCategory(str, enum.Enum):
    LICENSE = "license"
    REGISTRATION = "registration"
    INSURANCE = "insurance"
    IDENTITY = "identity"
    BETA_APPROVAL = "beta_approval"


class DriverDocumentStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class DriverDocumentStorageMode(str, enum.Enum):
    METADATA_ONLY = "metadata_only"
    LOCAL_DEV = "local_dev"
    OBJECT_STORAGE = "object_storage"


class DriverDocument(Base):
    __tablename__ = "driver_documents"
    __table_args__ = (
        UniqueConstraint("driver_id", "category", name="uq_driver_documents_driver_category"),
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="ck_driver_documents_size_bytes_nonneg",
        ),
    )

    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, default=DriverDocumentStatus.PENDING_REVIEW.value)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(128), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    storage_mode = Column(String(32), nullable=False, default=DriverDocumentStorageMode.METADATA_ONLY.value)
    storage_key = Column(String(512), nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
