"""Lease contract PDF generation and management."""

import os
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from models.land_listing import LandListing
from models.lease_contract import LeaseContract
from models.lease_inquiry import LeaseInquiry
from models.user import User

CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "data" / "contracts"
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

# Default lease pricing: INR per hectare per year (demo rate)
DEFAULT_ANNUAL_RATE_INR_PER_HA = 5000.0


def create_contract_from_inquiry(db: Session, inquiry: LeaseInquiry) -> LeaseContract:
    """Create a DRAFT lease contract when a landowner accepts an inquiry."""
    listing = db.query(LandListing).filter(LandListing.id == inquiry.listing_id).first()
    if not listing:
        raise ValueError("Listing not found")

    lease_years = inquiry.proposed_lease_years or listing.lease_duration_years
    annual_lease = round(listing.area_ha * DEFAULT_ANNUAL_RATE_INR_PER_HA, 2)
    total_lease = round(annual_lease * lease_years, 2)

    contract = LeaseContract(
        inquiry_id=inquiry.id,
        listing_id=listing.id,
        landowner_user_id=listing.owner_user_id,
        company_user_id=inquiry.company_user_id,
        lease_years=lease_years,
        area_ha=listing.area_ha,
        annual_lease_inr=annual_lease,
        total_lease_inr=total_lease,
        payment_amount_inr=total_lease,
        status="DRAFT",
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    # Generate initial PDF
    generate_contract_pdf(db, contract)
    return contract


def generate_contract_pdf(db: Session, contract: LeaseContract) -> str:
    """Generate a PDF for the lease contract and store the path."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError:
        # reportlab not installed — store placeholder
        contract.pdf_path = None
        contract.notes = (contract.notes or "") + " [PDF generation unavailable — install reportlab]"
        db.commit()
        return ""

    landowner = db.query(User).filter(User.id == contract.landowner_user_id).first()
    company = db.query(User).filter(User.id == contract.company_user_id).first()
    listing = db.query(LandListing).filter(LandListing.id == contract.listing_id).first()

    filename = f"lease_contract_{contract.id}.pdf"
    filepath = CONTRACTS_DIR / filename

    c = canvas.Canvas(str(filepath), pagesize=A4)
    width, height = A4
    y = height - 40 * mm

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, y, "CARBON CREDIT LAND LEASE AGREEMENT")
    y -= 10 * mm
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, y, f"Contract #{contract.id} — Generated {datetime.utcnow().strftime('%d %B %Y')}")
    y -= 8 * mm
    c.drawCentredString(width / 2, y, "CarbonChain Platform — Mumbai / Thane Region")
    y -= 15 * mm

    # Horizontal line
    c.setStrokeColorRGB(0.13, 0.77, 0.37)
    c.setLineWidth(1.5)
    c.line(30 * mm, y, width - 30 * mm, y)
    y -= 12 * mm

    # Parties
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "PARTIES")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    lines = [
        f"Landowner (Lessor): {landowner.full_name if landowner else 'Unknown'}",
        f"  Organization: {landowner.organization if landowner else '—'}",
        f"  Email: {landowner.email if landowner else '—'}",
        "",
        f"Company (Lessee): {company.full_name if company else 'Unknown'}",
        f"  Organization: {company.organization if company else '—'}",
        f"  Email: {company.email if company else '—'}",
    ]
    for line in lines:
        c.drawString(30 * mm, y, line)
        y -= 5 * mm
    y -= 5 * mm

    # Land Details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "LAND DETAILS")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    land_lines = [
        f"Listing: {listing.title if listing else '—'}",
        f"Location: {listing.location_label if listing else '—'}",
        f"Area: {contract.area_ha} hectares",
        f"Coordinates: {listing.lat}, {listing.lon}" if listing else "",
    ]
    for line in land_lines:
        if line:
            c.drawString(30 * mm, y, line)
            y -= 5 * mm
    y -= 5 * mm

    # Lease Terms
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "LEASE TERMS")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    terms = [
        f"Duration: {contract.lease_years} years",
        f"Annual Lease Amount: INR {contract.annual_lease_inr:,.2f}",
        f"Total Lease Amount: INR {contract.total_lease_inr:,.2f}",
        f"Payment Amount Due: INR {contract.payment_amount_inr:,.2f}",
        "",
        "Carbon Credit Estimates (PRELIMINARY — not verified issued credits):",
        f"  Estimated Annual Credits: {listing.estimated_annual_credits_tco2 or '—'} tCO2e/yr" if listing else "",
        f"  Estimated Total Credits: {listing.estimated_total_credits_tco2 or '—'} tCO2e" if listing else "",
    ]
    for line in terms:
        if line is not None:
            c.drawString(30 * mm, y, line)
            y -= 5 * mm
    y -= 10 * mm

    # Signatures section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "SIGNATURES")
    y -= 10 * mm
    c.setFont("Helvetica", 10)

    # Landowner signature
    c.drawString(30 * mm, y, "Landowner Signature:")
    if contract.landowner_signature:
        c.setFont("Helvetica-Oblique", 12)
        c.drawString(75 * mm, y, contract.landowner_signature)
        c.setFont("Helvetica", 9)
        c.drawString(75 * mm, y - 5 * mm, f"Signed: {contract.landowner_signed_at.strftime('%d %B %Y %H:%M UTC') if contract.landowner_signed_at else '—'}")
    else:
        c.drawString(75 * mm, y, "________________________ (pending)")
    y -= 15 * mm

    # Company signature
    c.drawString(30 * mm, y, "Company Signature:")
    if contract.company_signature:
        c.setFont("Helvetica-Oblique", 12)
        c.drawString(75 * mm, y, contract.company_signature)
        c.setFont("Helvetica", 9)
        c.drawString(75 * mm, y - 5 * mm, f"Signed: {contract.company_signed_at.strftime('%d %B %Y %H:%M UTC') if contract.company_signed_at else '—'}")
    else:
        c.drawString(75 * mm, y, "________________________ (pending)")
    y -= 15 * mm

    # Payment status
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "PAYMENT STATUS")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    c.drawString(30 * mm, y, f"Status: {contract.payment_status}")
    if contract.payment_reference:
        y -= 5 * mm
        c.drawString(30 * mm, y, f"Reference: {contract.payment_reference}")
    if contract.paid_at:
        y -= 5 * mm
        c.drawString(30 * mm, y, f"Paid: {contract.paid_at.strftime('%d %B %Y %H:%M UTC')}")
    y -= 15 * mm

    # Disclaimer
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(30 * mm, y, "DISCLAIMER: All carbon credit figures are preliminary estimates — not verified issued carbon credits.")
    y -= 4 * mm
    c.drawString(30 * mm, y, "This contract is generated by CarbonChain platform for demonstration purposes.")

    c.save()

    contract.pdf_path = str(filepath)
    db.commit()
    return str(filepath)


def contract_to_dict(contract: LeaseContract, db: Session) -> dict:
    """Convert a LeaseContract to a JSON-serializable dict."""
    landowner = db.query(User).filter(User.id == contract.landowner_user_id).first()
    company = db.query(User).filter(User.id == contract.company_user_id).first()
    listing = db.query(LandListing).filter(LandListing.id == contract.listing_id).first()
    return {
        "id": contract.id,
        "inquiry_id": contract.inquiry_id,
        "listing_id": contract.listing_id,
        "listing_title": listing.title if listing else None,
        "landowner_name": landowner.full_name if landowner else None,
        "landowner_org": landowner.organization if landowner else None,
        "company_name": company.full_name if company else None,
        "company_org": company.organization if company else None,
        "lease_years": contract.lease_years,
        "area_ha": contract.area_ha,
        "annual_lease_inr": contract.annual_lease_inr,
        "total_lease_inr": contract.total_lease_inr,
        "status": contract.status,
        "landowner_signed": contract.landowner_signature is not None,
        "landowner_signed_at": contract.landowner_signed_at.isoformat() if contract.landowner_signed_at else None,
        "company_signed": contract.company_signature is not None,
        "company_signed_at": contract.company_signed_at.isoformat() if contract.company_signed_at else None,
        "payment_amount_inr": contract.payment_amount_inr,
        "payment_status": contract.payment_status,
        "payment_reference": contract.payment_reference,
        "paid_at": contract.paid_at.isoformat() if contract.paid_at else None,
        "has_pdf": contract.pdf_path is not None,
        "created_at": contract.created_at.isoformat() if contract.created_at else None,
    }
