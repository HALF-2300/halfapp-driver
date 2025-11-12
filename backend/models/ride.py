from sqlalchemy import Column, Integer, String
from database import Base

class Ride(Base):
    __tablename__ = "rides"
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    driver_id = Column(Integer, index=True)
    status = Column(String, default="requested")