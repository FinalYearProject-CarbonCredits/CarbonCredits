from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class KYCRecord(Base):
    __tablename__ = "kyc_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False, unique=True)
    status = Column(String, default="NOT_STARTED")
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    id_document_ref = Column(String, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_admin_id = Column(Integer, nullable=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
