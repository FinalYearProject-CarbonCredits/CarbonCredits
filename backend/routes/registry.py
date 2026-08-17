"""Public registry serial lookup for issued carbon credits."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.credit_issuance import CreditIssuance
from services.issuance_service import DISCLAIMER, issuance_to_dict

router = APIRouter(prefix="/api/registry", tags=["Registry"])


@router.get("/credits/{serial}")
def lookup_serial(serial: str, db: Session = Depends(get_db)):
    """Look up an issued credit by registry / CarbonChain tracking serial."""
    rec = (
        db.query(CreditIssuance)
        .filter(CreditIssuance.registry_serial_number == serial.strip())
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Serial not found")
    if rec.status != "ISSUED":
        raise HTTPException(status_code=404, detail="Serial not found")
    data = issuance_to_dict(rec, db)
    return {
        "serial": rec.registry_serial_number,
        "status": rec.status,
        "registry": data["registry_label"],
        "methodology": rec.methodology,
        "issued_total_tco2e": rec.issued_total_tco2e,
        "verified_annual_tco2e": rec.verified_annual_tco2e,
        "listing_title": data["listing_title"],
        "issued_at": data["issued_at"],
        "verifier_name": rec.verifier_name,
        "disclaimer": DISCLAIMER,
    }
