from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from database import Base
from services.datetime_utils import utc_now_naive

class Ride(Base):
    __tablename__ = "rides"
    __table_args__ = (
        CheckConstraint(
            "status IN ('requested', 'offered', 'accepted', 'driver_arrived', "
            "'in_progress', 'completed', 'cancelled')",
            name="ck_rides_status_known",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    # Nullable for legacy rows; required to authorize rider-side cancel.
    customer_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    status = Column(String, default="requested", nullable=False)
    
    # Enhanced fields for earnings and tracking
    pickup_location = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    pickup_latitude = Column(Float, nullable=True)
    pickup_longitude = Column(Float, nullable=True)
    dropoff_latitude = Column(Float, nullable=True)
    dropoff_longitude = Column(Float, nullable=True)
    fare_amount = Column(Float, default=0.0)
    distance = Column(Float, default=0.0)  # in kilometers
    duration = Column(Integer, default=0)  # in minutes
    
    # Timestamps for performance tracking
    created_at = Column(DateTime, default=utc_now_naive)
    accepted_at = Column(DateTime, nullable=True)
    arrived_pickup_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Last decline / cancel explanation (not map or ETA data)
    lifecycle_reason = Column(Text, nullable=True)

    # v0.1 map route foundation (visual OSM/Leaflet; paid providers off by default)
    route_provider = Column(String, nullable=True)
    traffic_provider = Column(String, nullable=True)
    traffic_aware = Column(Boolean, nullable=True)
    traffic_signal_aware = Column(Boolean, nullable=True)
    route_confidence = Column(String, nullable=True)
    route_calculated_at = Column(DateTime, nullable=True)
    google_maps_fallback_enabled = Column(Boolean, nullable=True, default=False)
    mapbox_traffic_enabled = Column(Boolean, nullable=True, default=False)

    # RIDE-003 sequential dispatch offer (v0.1 — in-process timeout; production scheduler later)
    dispatch_driver_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    dispatch_expires_at = Column(DateTime, nullable=True)
    dispatch_attempt_count = Column(Integer, default=0, nullable=False)

    # Additional metadata
    notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # Customer rating (1-5)


Index("ix_rides_status_driver_id", Ride.status, Ride.driver_id)
Index("ix_rides_created_at", Ride.created_at)