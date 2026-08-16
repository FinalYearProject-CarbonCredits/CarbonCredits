"""Verified carbon credit issuance workflow (Verra / Gold Standard style).

IMPORTANT SCOPE NOTE: Verra and Gold Standard do not expose public APIs for
carbon credit issuance. Real issuance is a manual process — project
documentation is submitted through the registry's own portal and reviewed
by an accredited, independent third-party auditor (a "Validation and
Verification Body"), a process that typically takes months. This service
models that workflow end-to-end (submit -> under third-party verification
-> verified -> registry-issued) so CarbonChain can track status and keep an
audit trail, but it does NOT call any live registry API and does NOT
constitute real issuance. `registry_serial_number` should only be filled in
once a human has actually completed real registry submission outside this
platform.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.credit_issuance import CreditIssuance
from models.land_listing import LandListing

VALID_REGISTRIES = {"VERRA", "GOLD_STANDARD"}

# Small illustrative set of real methodology codes used by these registries.
VALID_METHODOLOGIES = {
    "VM0033",       # Verra — Tidal Wetland and Seagrass Restoration
    "VM0007",       # Verra — REDD+ Methodology Framework
    "AR-ACM0003",   # CDM/Verra — Afforestation and Reforestation
    "AR-AMS0007",   # CDM — Small-scale Afforestation/Reforestation
    "GS4GG-LR",     # Gold Standard — Land Use & Forests
    "OTHER",
}

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
    "registry submission and review by an accredited independent third-party auditor."
)


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


def issuance_to_dict(rec: CreditIssuance, db: Session) -> dict[str, Any]:
    listing = db.query(LandListing).filter(LandListing.id == rec.listing_id).first()
    return {
        "id": rec.id,
        "listing_id": rec.listing_id,
        "listing_title": listing.title if listing else None,
        "parcel_id": rec.parcel_id,
        "registry": rec.registry,
        "methodology": rec.methodology,
        "status": rec.status,
        "preliminary_annual_tco2e": rec.preliminary_annual_tco2e,
        "verified_annual_tco2e": rec.verified_annual_tco2e,
        "issued_total_tco2e": rec.issued_total_tco2e,
        "verifier_name": rec.verifier_name,
        "verifier_notes": rec.verifier_notes,
        "registry_serial_number": rec.registry_serial_number,
        "evidence_notes": rec.evidence_notes,
        "submitted_at": rec.submitted_at.isoformat() if rec.submitted_at else None,
        "verification_started_at": rec.verification_started_at.isoformat() if rec.verification_started_at else None,
        "verified_at": rec.verified_at.isoformat() if rec.verified_at else None,
        "issued_at": rec.issued_at.isoformat() if rec.issued_at else None,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "disclaimer": DISCLAIMER,
    }
