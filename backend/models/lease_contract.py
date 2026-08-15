from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base


class LeaseContract(Base):
    __tablename__ = "lease_contracts"

    id = Column(Integer, primary_key=True, index=True)
    inquiry_id = Column(Integer, unique=True, index=True, nullable=False)
    listing_id = Column(Integer, index=True, nullable=False)
    landowner_user_id = Column(Integer, index=True, nullable=False)
    company_user_id = Column(Integer, index=True, nullable=False)

    lease_years = Column(Integer, nullable=False)
    area_ha = Column(Float, nullable=False)
    annual_lease_inr = Column(Float, nullable=False)
    total_lease_inr = Column(Float, nullable=False)

    pdf_path = Column(String, nullable=True)
    status = Column(String, default="DRAFT")
    landowner_signed_at = Column(DateTime, nullable=True)
    landowner_signature = Column(String, nullable=True)
    company_signed_at = Column(DateTime, nullable=True)
    company_signature = Column(String, nullable=True)

    payment_amount_inr = Column(Float, nullable=True)
    payment_reference = Column(String, nullable=True)
    payment_status = Column(String, default="UNPAID")
    paid_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)
