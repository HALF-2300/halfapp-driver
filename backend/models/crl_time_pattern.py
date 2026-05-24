"""Time-of-day demand baselines per H3 cell."""

from sqlalchemy import Column, Float, Integer, String

from database import Base


class CrlTimePattern(Base):
    __tablename__ = "crl_time_pattern"

    id = Column(Integer, primary_key=True)
    h3 = Column(String(32), nullable=False, index=True)
    hour_of_day = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)
    avg_demand = Column(Float, nullable=False, default=0.0)
    avg_supply = Column(Float, nullable=False, default=0.0)
    baseline_wait_seconds = Column(Float, nullable=True)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
