from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from database import Base
from services.datetime_utils import utc_now_naive

SNAPSHOT_ROLE_QUOTE = "quote"
SNAPSHOT_ROLE_ACCEPT = "accept"
SNAPSHOT_ROLE_COMPLETE = "complete"
SNAPSHOT_ROLE_REFRESH = "refresh"
SNAPSHOT_ROLE_DIAGNOSTIC = "diagnostic"

ALLOWED_SNAPSHOT_ROLES = frozenset(
    {
        SNAPSHOT_ROLE_QUOTE,
        SNAPSHOT_ROLE_ACCEPT,
        SNAPSHOT_ROLE_COMPLETE,
        SNAPSHOT_ROLE_REFRESH,
        SNAPSHOT_ROLE_DIAGNOSTIC,
    }
)


class RouteSnapshot(Base):
    __tablename__ = "route_snapshots"
    __table_args__ = (
        CheckConstraint(
            "snapshot_role IN ('quote', 'accept', 'complete', 'refresh', 'diagnostic')",
            name="ck_route_snapshots_role_known",
        ),
        CheckConstraint("distance_meters >= 0", name="ck_route_snapshots_distance_nonneg"),
        CheckConstraint("duration_seconds >= 0", name="ck_route_snapshots_duration_nonneg"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_role = Column(String, nullable=False)
    route_provider = Column(String, nullable=False)
    used_fallback = Column(Boolean, nullable=False, default=False)
    distance_meters = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Integer, nullable=False, default=0)
    geometry_polyline = Column(Text, nullable=True)
    geometry_hash = Column(String, nullable=True)
    request_hash = Column(String, nullable=True)
    response_hash = Column(String, nullable=True)
    provenance_json = Column(Text, nullable=True)
    pricing_id = Column(Integer, ForeignKey("ride_pricing.ride_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive, nullable=False)
