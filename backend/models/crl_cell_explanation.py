"""Cause attribution output per cell bucket."""

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base
from services.crl_labels import CRL_LABEL_VERSION
from services.datetime_utils import utc_now_naive


class CrlCellExplanation(Base):
    __tablename__ = "crl_cell_explanation"

    id = Column(Integer, primary_key=True)
    h3 = Column(String(32), nullable=False, index=True)
    bucket_start_ts = Column(DateTime, nullable=False, index=True)
    primary_cause = Column(String(64), nullable=False)
    secondary_causes_json = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    signals_used_json = Column(Text, nullable=False)
    driver_label = Column(Text, nullable=False)
    label_version = Column(String(32), nullable=False, default=CRL_LABEL_VERSION)
    computed_at = Column(DateTime, nullable=False, default=utc_now_naive)
