from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class LeaseInquiry(Base):
    __tablename__ = "lease_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, index=True, nullable=False)
    company_user_id = Column(Integer, index=True, nullable=False)
    message = Column(Text, nullable=False)
    proposed_lease_years = Column(Integer, nullable=True)
    status = Column(String, default="SUBMITTED")  # SUBMITTED | ACCEPTED | DECLINED | CLOSED
    landowner_response = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
