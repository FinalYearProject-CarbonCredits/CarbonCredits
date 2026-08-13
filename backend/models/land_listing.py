from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from database import Base


class LandListing(Base):
    __tablename__ = "land_listings"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, index=True, nullable=False)
    parcel_id = Column(Integer, nullable=True)
    title = Column(String, nullable=False)
    location_label = Column(String, nullable=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    area_ha = Column(Float, nullable=False)
    lease_duration_years = Column(Integer, nullable=False)
    lease_type = Column(String, default="land_lease")
    available = Column(Boolean, default=True)
    estimated_annual_credits_tco2 = Column(Float, nullable=True)
    estimated_total_credits_tco2 = Column(Float, nullable=True)
    preliminary_only = Column(Boolean, default=True)
    status = Column(String, default="active")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
