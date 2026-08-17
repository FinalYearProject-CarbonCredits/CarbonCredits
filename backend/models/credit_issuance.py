from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base


class CreditIssuance(Base):
    """
    Tracks the path from a preliminary listing estimate to a registry-issued
    carbon credit (Verra VCS / Gold Standard style). This models the offline,
    auditor-driven workflow those registries actually use — it does not call
    any live registry API (neither Verra nor Gold Standard expose one for
    issuance). registry_serial_number is only a live registry ID once a human
    pastes the serial issued outside this platform; otherwise it is a
    CarbonChain tracking serial.
    """

    __tablename__ = "credit_issuances"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, index=True, nullable=False)
    parcel_id = Column(Integer, nullable=True)
    owner_user_id = Column(Integer, index=True, nullable=False)

    registry = Column(String, default="VERRA")  # VERRA | GOLD_STANDARD
    methodology = Column(String, nullable=True)  # e.g. VM0033, AR-ACM0003

    # NOT_SUBMITTED -> SUBMITTED -> UNDER_VERIFICATION -> VERIFIED -> ISSUED
    # any of SUBMITTED / UNDER_VERIFICATION / VERIFIED can move to REJECTED
    status = Column(String, default="NOT_SUBMITTED")

    preliminary_annual_tco2e = Column(Float, nullable=True)
    verified_annual_tco2e = Column(Float, nullable=True)
    issued_total_tco2e = Column(Float, nullable=True)

    verifier_name = Column(String, nullable=True)
    verifier_notes = Column(Text, nullable=True)
    registry_serial_number = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)

    evidence_notes = Column(Text, nullable=True)

    submitted_at = Column(DateTime, nullable=True)
    verification_started_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    issued_at = Column(DateTime, nullable=True)

    reviewed_by_admin_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
