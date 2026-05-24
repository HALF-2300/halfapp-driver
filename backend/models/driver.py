from sqlalchemy import Column, Integer, String
from database import Base

class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True, index=True)
    license_no = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)