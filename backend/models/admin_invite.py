from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from database import Base

class AdminInvite(Base):
    __tablename__ = "admin_invites"
    
    id = Column(Integer, primary_key=True, index=True)
    access_code = Column(String, unique=True, index=True, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    used_by_email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Optional metadata
    created_by = Column(String, nullable=True)  # Which admin created this invite
    description = Column(String, nullable=True)  # Purpose of invite