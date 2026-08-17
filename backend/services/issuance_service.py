"""Verified carbon credit issuance workflow (Verra / Gold Standard style).

IMPORTANT SCOPE NOTE: Verra and Gold Standard do not expose public APIs for
carbon credit issuance. Real issuance is a manual process — project
documentation is submitted through the registry's own portal and reviewed
by an accredited, independent third-party auditor (a "Validation and
Verification Body"), a process that typically takes months. This service
models that workflow end-to-end (submit -> under third-party verification
-> verified -> registry-issued) so CarbonChain can track status and keep an
audit trail, but it does NOT call any live registry API and does NOT
constitute real issuance. `registry_serial_number` should only be treated as
a live registry ID once a human has pasted the serial issued outside this
platform; otherwise it is a CarbonChain tracking serial.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models.credit_issuance import CreditIssuance
from models.land_listing import LandListing
from models.land_parcel import LandParcel
from models.user import User

VALID_REGISTRIES = {"VERRA", "GOLD_STANDARD"}

# Methodology codes accepted per registry (illustrative real codes).
REGISTRY_METHODOLOGIES: dict[str, set[str]] = {
    "VERRA": {
        "VM0007",       # REDD+ Methodology Framework
        "VM0033",       # Tidal Wetland and Seagrass Restoration
        "AR-ACM0003",   # Afforestation and Reforestation of degraded land
        "AR-AMS0007",   # Small-scale A/R
        "OTHER",
    },
    "GOLD_STANDARD": {
        "GS4GG-LR",     # Gold Standard Land Use & Forests
        "AR-ACM0003",
        "OTHER",
    },
}

VALID_METHODOLOGIES = set().union(*REGISTRY_METHODOLOGIES.values())

STATUS_FLOW: dict[str, set[str]] = {
    "NOT_SUBMITTED": {"SUBMITTED"},
    "SUBMITTED": {"UNDER_VERIFICATION", "REJECTED"},
    "UNDER_VERIFICATION": {"VERIFIED", "REJECTED"},
    "VERIFIED": {"ISSUED", "REJECTED"},
    "ISSUED": set(),
    "REJECTED": {"SUBMITTED"},
}

DISCLAIMER = (
    "Tracks a Verra/Gold Standard-style verification & issuance workflow for audit purposes. "
    "No live registry API is called at any stage — real issuance still requires manual "
    "registry submission and review by an accredited independent third-party auditor (VVB)."
)

CERTS_DIR = Path(__file__).resolve().parent.parent / "data" / "certificates"
CERTS_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_LABELS = {
    "VERRA": "Verra VCS",
    "GOLD_STANDARD": "Gold Standard for the Global Goals",
}


def validate_registry_methodology(registry: str, methodology: str) -> None:
    registry = (registry or "").upper()
    methodology = (methodology or "").strip()
    if registry not in VALID_REGISTRIES:
        raise ValueError(f"registry must be one of {sorted(VALID_REGISTRIES)}")
    allowed = REGISTRY_METHODOLOGIES[registry]
    if methodology not in allowed:
        raise ValueError(
            f"methodology {methodology} is not valid for {registry}. "
            f"Allowed: {sorted(allowed)}"
        )


def generate_tracking_serial(rec: CreditIssuance) -> str:
    """Internal tracking serial until a real registry ID is pasted by admin."""
    prefix = "VCS" if rec.registry == "VERRA" else "GS"
    year = datetime.utcnow().year
    return f"CC-TRACK-{prefix}-IN-MH-{rec.id:05d}-{year}"


def advance_status(rec: CreditIssuance, new_status: str) -> None:
    """
    Move an issuance record to new_status if the transition is legal, else raise ValueError.

    NOTE: rec.status may be None here rather than "NOT_SUBMITTED" — SQLAlchemy
    Column(default=...) is only applied at INSERT time, not at object
    construction. So a freshly-built CreditIssuance() that hasn't been through
    db.add()/commit() yet will have status=None even though the model default
    is "NOT_SUBMITTED". Treat None as NOT_SUBMITTED for the transition check.
    """
    current = rec.status or "NOT_SUBMITTED"
    allowed = STATUS_FLOW.get(current, set())
    if new_status not in allowed:
        raise ValueError(
            f"Cannot move issuance from {current} to {new_status}. "
            f"Allowed next states: {sorted(allowed) or 'none — terminal'}"
        )
    rec.status = new_status
    now = datetime.utcnow()
    if new_status == "SUBMITTED":
        rec.submitted_at = now
    elif new_status == "UNDER_VERIFICATION":
        rec.verification_started_at = now
    elif new_status == "VERIFIED":
        rec.verified_at = now
    elif new_status == "ISSUED":
        rec.issued_at = now


def apply_review_rules(rec: CreditIssuance, new_status: str) -> None:
    """Extra field requirements at each review stage (third-party VVB + serial)."""
    if new_status == "UNDER_VERIFICATION" and not (rec.verifier_name or "").strip():
        raise ValueError("Assign a third-party verifier (VVB) name before starting verification")
    if new_status == "VERIFIED":
        if not (rec.verifier_name or "").strip():
            raise ValueError("Verifier (VVB) name is required to mark VERIFIED")
        if rec.verified_annual_tco2e is None or rec.verified_annual_tco2e <= 0:
            raise ValueError("verified_annual_tco2e is required to mark VERIFIED")
    if new_status == "ISSUED":
        if rec.verified_annual_tco2e is None or rec.verified_annual_tco2e <= 0:
            raise ValueError("verified_annual_tco2e is required before issuance")
        if rec.issued_total_tco2e is None or rec.issued_total_tco2e <= 0:
            rec.issued_total_tco2e = rec.verified_annual_tco2e
        if not (rec.registry_serial_number or "").strip():
            rec.registry_serial_number = generate_tracking_serial(rec)


def apply_issued_to_listing(db: Session, rec: CreditIssuance) -> None:
    """Once issued, listing figures become verified (no longer preliminary-only)."""
    listing = db.query(LandListing).filter(LandListing.id == rec.listing_id).first()
    if not listing:
        return
    listing.preliminary_only = False
    if rec.verified_annual_tco2e:
        listing.estimated_annual_credits_tco2 = rec.verified_annual_tco2e
    if rec.issued_total_tco2e:
        listing.estimated_total_credits_tco2 = rec.issued_total_tco2e


def latest_issuance_for_listing(db: Session, listing_id: int) -> CreditIssuance | None:
    return (
        db.query(CreditIssuance)
        .filter(CreditIssuance.listing_id == listing_id)
        .order_by(CreditIssuance.created_at.desc())
        .first()
    )


def issuance_summary(rec: CreditIssuance | None) -> dict[str, Any] | None:
    if not rec:
        return None
    return {
        "id": rec.id,
        "status": rec.status,
        "registry": rec.registry,
        "registry_label": REGISTRY_LABELS.get(rec.registry, rec.registry),
        "methodology": rec.methodology,
        "preliminary_annual_tco2e": rec.preliminary_annual_tco2e,
        "verified_annual_tco2e": rec.verified_annual_tco2e,
        "issued_total_tco2e": rec.issued_total_tco2e,
        "registry_serial_number": rec.registry_serial_number,
        "verifier_name": rec.verifier_name,
        "issued_at": rec.issued_at.isoformat() if rec.issued_at else None,
        "preliminary_only": rec.status != "ISSUED",
    }


def generate_issuance_certificate(db: Session, rec: CreditIssuance) -> str:
    """PDF certificate for verified / issued credits. Empty string if reportlab missing."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError:
        return ""

    listing = db.query(LandListing).filter(LandListing.id == rec.listing_id).first()
    owner = db.query(User).filter(User.id == rec.owner_user_id).first()
    parcel = db.query(LandParcel).filter(LandParcel.id == rec.parcel_id).first() if rec.parcel_id else None

    filename = f"issuance_certificate_{rec.id}.pdf"
    filepath = CERTS_DIR / filename
    c = canvas.Canvas(str(filepath), pagesize=A4)
    width, height = A4
    y = height - 35 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, "CARBONCHAIN — CREDIT ISSUANCE CERTIFICATE")
    y -= 8 * mm
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, y, "Verra / Gold Standard style tracking record (not a live registry instrument)")
    y -= 14 * mm

    def line(label: str, value: str) -> None:
        nonlocal y
        c.setFont("Helvetica-Bold", 10)
        c.drawString(25 * mm, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(85 * mm, y, value[:90])
        y -= 7 * mm

    line("Status", rec.status or "")
    line("Registry", REGISTRY_LABELS.get(rec.registry, rec.registry or ""))
    line("Methodology", rec.methodology or "—")
    line("Serial / tracking ID", rec.registry_serial_number or "—")
    line("Project / listing", (listing.title if listing else f"Listing #{rec.listing_id}") or "—")
    line("Landowner", (owner.full_name if owner else "—") or "—")
    if parcel:
        line("Survey / plot", f"{parcel.survey_number or '—'} / {parcel.plot_number or '—'}")
        line("Village", f"{parcel.village or '—'}, {parcel.district or '—'}")
        line("Area", f"{parcel.area_ha} ha")
    line("Preliminary tCO2e/yr", str(rec.preliminary_annual_tco2e or "—"))
    line("Verified tCO2e/yr", str(rec.verified_annual_tco2e or "—"))
    line("Issued total tCO2e", str(rec.issued_total_tco2e or "—"))
    line("Third-party VVB", rec.verifier_name or "—")
    line("Submitted", rec.submitted_at.isoformat() if rec.submitted_at else "—")
    line("Verified", rec.verified_at.isoformat() if rec.verified_at else "—")
    line("Issued", rec.issued_at.isoformat() if rec.issued_at else "—")

    y -= 6 * mm
    c.setFont("Helvetica-Oblique", 8)
    for wrap in _wrap(DISCLAIMER, 95):
        c.drawString(25 * mm, y, wrap)
        y -= 4.5 * mm
    if rec.verifier_notes:
        y -= 4 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y, "Verifier notes")
        y -= 5 * mm
        c.setFont("Helvetica", 8)
        for wrap in _wrap(rec.verifier_notes, 95):
            c.drawString(25 * mm, y, wrap)
            y -= 4.5 * mm

    c.save()
    rec.pdf_path = str(filepath)
    return str(filepath)


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if len(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def issuance_to_dict(rec: CreditIssuance, db: Session) -> dict[str, Any]:
    listing = db.query(LandListing).filter(LandListing.id == rec.listing_id).first()
    return {
        "id": rec.id,
        "listing_id": rec.listing_id,
        "listing_title": listing.title if listing else None,
        "parcel_id": rec.parcel_id,
        "registry": rec.registry,
        "registry_label": REGISTRY_LABELS.get(rec.registry, rec.registry),
        "methodology": rec.methodology,
        "status": rec.status,
        "preliminary_annual_tco2e": rec.preliminary_annual_tco2e,
        "verified_annual_tco2e": rec.verified_annual_tco2e,
        "issued_total_tco2e": rec.issued_total_tco2e,
        "verifier_name": rec.verifier_name,
        "verifier_notes": rec.verifier_notes,
        "registry_serial_number": rec.registry_serial_number,
        "evidence_notes": rec.evidence_notes,
        "has_certificate": bool(rec.pdf_path),
        "submitted_at": rec.submitted_at.isoformat() if rec.submitted_at else None,
        "verification_started_at": rec.verification_started_at.isoformat() if rec.verification_started_at else None,
        "verified_at": rec.verified_at.isoformat() if rec.verified_at else None,
        "issued_at": rec.issued_at.isoformat() if rec.issued_at else None,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "next_statuses": sorted(STATUS_FLOW.get(rec.status or "NOT_SUBMITTED", set())),
        "disclaimer": DISCLAIMER,
    }
