"""Tamper-evident proof receipts for route quotes and trips."""

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class ProofReceipt(Base):
    __tablename__ = "proof_receipts"

    id = Column(Integer, primary_key=True)
    subject = Column(String(64), nullable=False)
    subject_id = Column(Integer, nullable=False, index=True)
    proof_level = Column(String(32), nullable=False)
    proof_reason = Column(String(255), nullable=False)
    receipt_payload_json = Column(Text, nullable=False)
    receipt_hash = Column(String(64), nullable=False, index=True)
    signed_by = Column(String(64), nullable=False, default="halfapp-sil-v0.1")
    created_at = Column(DateTime, nullable=False, default=utc_now_naive, index=True)
