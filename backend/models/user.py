from sqlalchemy import Column, Integer, String, DateTime, func, Enum
from database import Base
import enum

class UserRole(enum.Enum):
    CUSTOMER = "customer"
    DRIVER = "driver"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    license_no = Column(String, unique=True, nullable=True)  # For drivers
    is_active = Column(String, default="true", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())