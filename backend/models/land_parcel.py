from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base


class LandParcel(Base):
    __tablename__ = "land_parcels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(String, nullable=True)
    owner_user_id = Column(Integer, index=True, nullable=True)

    # Exact boundary — area and centroid are ALWAYS computed server-side from geometry
    geometry_geojson = Column(Text, nullable=False)
    area_ha = Column(Float, nullable=False)
    centroid_lat = Column(Float, nullable=True)
    centroid_lon = Column(Float, nullable=True)

    # Land record details (must match uploaded document)
    survey_number = Column(String, nullable=True)
    plot_number = Column(String, nullable=True)
    village = Column(String, nullable=True)
    taluka = Column(String, nullable=True)
    district = Column(String, nullable=True)
    location_label = Column(String, nullable=True)

    # Uploaded land document (7/12, sale deed, etc.)
    document_type = Column(String, nullable=True)
    document_filename = Column(String, nullable=True)
    document_path = Column(String, nullable=True)
    declared_area_document_ha = Column(Float, nullable=True)  # from deed — admin cross-check only

    # Verification workflow
    verification_status = Column(String, default="PENDING")
    admin_notes = Column(Text, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verified_by_admin_id = Column(Integer, nullable=True)

    land_cover_dominant = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
