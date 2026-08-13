from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models.kyc import KYCRecord
from models.land_listing import LandListing
from models.lease_inquiry import LeaseInquiry
from models.land_parcel import LandParcel
from models.user import User
from schemas.auth import KYCReview, LandVerificationReview
from services.auth import require_roles
from services.land_registration import DOCS_DIR, parcel_to_dict

router = APIRouter(prefix="/api/admin", tags=["Admin"])
require_admin = require_roles("admin")


@router.get("/users")
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "full_name": u.full_name,
            "organization": u.organization,
            "phone": u.phone,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.get("/kyc/pending")
def pending_kyc(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    records = (
        db.query(KYCRecord)
        .filter(KYCRecord.status.in_(["SUBMITTED", "UNDER_REVIEW"]))
        .order_by(KYCRecord.submitted_at.desc())
        .all()
    )
    results = []
    for k in records:
        user = db.query(User).filter(User.id == k.user_id).first()
        results.append({
            "kyc_id": k.id,
            "user_id": k.user_id,
            "user_email": user.email if user else None,
            "full_name": k.full_name,
            "phone": k.phone,
            "address": k.address,
            "id_document_ref": k.id_document_ref,
            "status": k.status,
            "submitted_at": k.submitted_at.isoformat() if k.submitted_at else None,
        })
    return {"count": len(results), "pending": results}


@router.patch("/kyc/{user_id}")
def review_kyc(
    user_id: int,
    body: KYCReview,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    kyc = db.query(KYCRecord).filter(KYCRecord.user_id == user_id).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC record not found")

    kyc.status = body.status
    kyc.admin_notes = body.admin_notes
    kyc.reviewed_at = datetime.utcnow()
    kyc.reviewed_by_admin_id = admin.id
    db.commit()
    return {
        "message": f"KYC updated to {body.status}",
        "user_id": user_id,
        "status": kyc.status,
    }


@router.get("/listings")
def all_listings(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    listings = db.query(LandListing).order_by(LandListing.created_at.desc()).all()
    return [
        {
            "id": l.id,
            "owner_user_id": l.owner_user_id,
            "title": l.title,
            "area_ha": l.area_ha,
            "lease_duration_years": l.lease_duration_years,
            "available": l.available,
            "status": l.status,
        }
        for l in listings
    ]


@router.patch("/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot deactivate admin")
    user.is_active = not user.is_active
    db.commit()
    return {"user_id": user_id, "is_active": user.is_active}


@router.get("/land/pending")
def pending_land_verifications(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    parcels = (
        db.query(LandParcel)
        .filter(LandParcel.verification_status.in_(["PENDING", "UNDER_REVIEW"]))
        .order_by(LandParcel.created_at.desc())
        .all()
    )
    results = []
    for p in parcels:
        owner = db.query(User).filter(User.id == p.owner_user_id).first()
        data = parcel_to_dict(p)
        data["owner_email"] = owner.email if owner else None
        data["owner_name"] = owner.full_name if owner else None
        data["document_url"] = f"/api/admin/land/{p.id}/document"
        results.append(data)
    return {"count": len(results), "pending": results}


@router.get("/land/{parcel_id}/document")
def download_land_document(
    parcel_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    p = db.query(LandParcel).filter(LandParcel.id == parcel_id).first()
    if not p or not p.document_path:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(p.document_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Document file missing on server")
    return FileResponse(path, filename=p.document_filename or path.name)


@router.patch("/land/{parcel_id}")
def review_land(
    parcel_id: int,
    body: LandVerificationReview,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    p = db.query(LandParcel).filter(LandParcel.id == parcel_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Land parcel not found")

    p.verification_status = body.status
    p.admin_notes = body.admin_notes
    p.verified_at = datetime.utcnow() if body.status == "VERIFIED" else None
    p.verified_by_admin_id = admin.id if body.status == "VERIFIED" else None
    db.commit()
    return {
        "message": f"Land record updated to {body.status}",
        "parcel_id": parcel_id,
        "computed_area_ha": p.area_ha,
        "declared_area_document_ha": p.declared_area_document_ha,
    }


@router.get("/inquiries")
def all_lease_inquiries(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    inquiries = db.query(LeaseInquiry).order_by(LeaseInquiry.created_at.desc()).all()
    results = []
    for inq in inquiries:
        listing = db.query(LandListing).filter(LandListing.id == inq.listing_id).first()
        company = db.query(User).filter(User.id == inq.company_user_id).first()
        owner = db.query(User).filter(User.id == listing.owner_user_id).first() if listing else None
        results.append({
            "id": inq.id,
            "listing_id": inq.listing_id,
            "listing_title": listing.title if listing else None,
            "landowner": owner.full_name if owner else None,
            "company": company.full_name if company else None,
            "company_organization": company.organization if company else None,
            "message": inq.message,
            "proposed_lease_years": inq.proposed_lease_years,
            "status": inq.status,
            "landowner_response": inq.landowner_response,
            "created_at": inq.created_at.isoformat() if inq.created_at else None,
            "responded_at": inq.responded_at.isoformat() if inq.responded_at else None,
        })
    return {"count": len(results), "inquiries": results}
