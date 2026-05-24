from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum, Float, Index, Integer, String, func
from database import Base
import enum

class UserRole(enum.Enum):
    CUSTOMER = "customer"
    DRIVER = "driver"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("is_active IN (0, 1)", name="ck_users_is_active_bool"),
        Index("ix_users_email", "email"),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    license_no = Column(String, unique=True, nullable=True)  # For drivers
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Driver profile & presence (persisted for real driver-app flows)
    phone = Column(String, nullable=True)
    emergency_contact = Column(String, nullable=True)
    vehicle_make = Column(String, nullable=True)
    vehicle_model = Column(String, nullable=True)
    vehicle_year = Column(Integer, nullable=True)
    license_plate = Column(String, nullable=True)
    insurance_policy = Column(String, nullable=True)
    availability = Column(String, default="available", index=True, nullable=False)
    last_latitude = Column(Float, nullable=True)
    last_longitude = Column(Float, nullable=True)
    last_location_at = Column(DateTime(timezone=True), nullable=True)