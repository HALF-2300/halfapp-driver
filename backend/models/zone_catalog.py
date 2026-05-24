"""Static zone knowledge for cause attribution (airport, hospital, etc.)."""

from sqlalchemy import Column, Float, Integer, String, Text

from database import Base


class ZoneCatalog(Base):
    __tablename__ = "zone_catalog"

    zone_id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    zone_type = Column(String(32), nullable=False, index=True)
    h3_list_json = Column(Text, nullable=False)
    center_lat = Column(Float, nullable=True)
    center_lng = Column(Float, nullable=True)
    radius_m = Column(Float, nullable=True)
    priority_weight = Column(Float, nullable=False, default=1.0)
