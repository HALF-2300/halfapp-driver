"""Aggregated SIL hex cells (driver-visible when honesty gates pass)."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from database import Base
from services.datetime_utils import utc_now_naive


class SilCellAggregate(Base):
    __tablename__ = "sil_cell_aggregate"

    id = Column(Integer, primary_key=True)
    h3 = Column(String(32), nullable=False, index=True)
    bucket_start_ts = Column(DateTime, nullable=False, index=True)
    bucket_minutes = Column(Integer, nullable=False, default=5)
    demand_count = Column(Integer, nullable=False, default=0)
    supply_idle_count = Column(Integer, nullable=False, default=0)
    fleet_samples = Column(Integer, nullable=False, default=0)
    unique_drivers = Column(Integer, nullable=False, default=0)
    fleet_speed_p50_mps = Column(Float, nullable=True)
    congestion_score = Column(Float, nullable=False, default=0.0)
    busy_score = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=False, default=0.0)
    min_k_met = Column(Boolean, nullable=False, default=False)
    provenance_json = Column(Text, nullable=True)
    label_version = Column(String(32), nullable=False, default="sil_v0.1")
    computed_at = Column(DateTime, nullable=False, default=utc_now_naive)
