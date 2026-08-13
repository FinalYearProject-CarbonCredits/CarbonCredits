from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base


class CarbonAssessment(Base):
    __tablename__ = "carbon_assessments"

    id = Column(Integer, primary_key=True, index=True)
    parcel_id = Column(Integer, index=True, nullable=False)
    status = Column(String, default="PENDING")
    model_name = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
    mean_agbd = Column(Float, nullable=True)
    median_agbd = Column(Float, nullable=True)
    min_agbd = Column(Float, nullable=True)
    max_agbd = Column(Float, nullable=True)
    agbd_uncertainty = Column(Float, nullable=True)
    total_biomass_mg = Column(Float, nullable=True)
    carbon_stock_mgc = Column(Float, nullable=True)
    co2e_mg = Column(Float, nullable=True)
    carbon_fraction_used = Column(Float, nullable=True)
    valid_pixel_pct = Column(Float, nullable=True)
    satellite_source = Column(String, nullable=True)
    observation_date = Column(String, nullable=True)
    ndvi_mean = Column(Float, nullable=True)
    evi_mean = Column(Float, nullable=True)
    gedi_footprint_count = Column(Integer, default=0)
    assumptions_json = Column(Text, nullable=True)
    raster_path = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
