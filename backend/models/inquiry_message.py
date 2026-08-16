from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class InquiryMessage(Base):
    __tablename__ = "inquiry_messages"

    id = Column(Integer, primary_key=True, index=True)
    inquiry_id = Column(Integer, index=True, nullable=False)
    sender_user_id = Column(Integer, index=True, nullable=False)
    sender_role = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
