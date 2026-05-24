"""CRL per-cell activity snapshot (aggregated; driver-visible when gated)."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from database import Base
from services.datetime_utils import utc_now_naive


class CrlCellSnapshot(Base):
    __tablename__ = "crl_cell_snapshot"

    id = Column(Integer, primary_key=True)
    h3 = Column(String(32), nullable=False, index=True)
    bucket_start_ts = Column(DateTime, nullable=False, index=True)
    bucket_minutes = Column(Integer, nullable=False, default=5)
    demand_count = Column(Integer, nullable=False, default=0)
    pickup_count = Column(Integer, nullable=False, default=0)
    dropoff_count = Column(Integer, nullable=False, default=0)
    cancel_count = Column(Integer, nullable=False, default=0)
    cancel_rate = Column(Float, nullable=False, default=0.0)
    avg_wait_seconds = Column(Float, nullable=True)
    idle_driver_count = Column(Integer, nullable=False, default=0)
    supply_demand_ratio = Column(Float, nullable=True)
    demand_score = Column(Float, nullable=False, default=0.0)
    wait_score = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=False, default=0.0)
    min_k_met = Column(Boolean, nullable=False, default=False)
    unique_drivers = Column(Integer, nullable=False, default=0)
    computed_at = Column(DateTime, nullable=False, default=utc_now_naive)
