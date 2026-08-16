from datetime import datetime



from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session



from database import get_db

from models.kyc import KYCRecord

from models.land_listing import LandListing

from models.land_parcel import LandParcel

from models.lease_inquiry import LeaseInquiry

from models.user import User

from schemas.auth import LeaseInquiryCreate, ContractSign, PaymentRecord, MessageCreate
from services.auth import require_roles
from models.lease_contract import LeaseContract
from models.inquiry_message import InquiryMessage
from services.contract_service import contract_to_dict, generate_contract_pdf



router = APIRouter(prefix="/api/company", tags=["Company"])



require_company = require_roles("company")





@router.get("/available-landowners")

def available_landowners(

    user: User = Depends(require_company),

    db: Session = Depends(get_db),

):

    verified_user_ids = [

        k.user_id

        for k in db.query(KYCRecord).filter(KYCRecord.status == "VERIFIED").all()

    ]

    if not verified_user_ids:

        return {"count": 0, "landowners": [], "note": "No KYC-verified landowners available yet"}



    listings = (

        db.query(LandListing)

        .filter(

            LandListing.owner_user_id.in_(verified_user_ids),

            LandListing.available == True,

            LandListing.status == "active",

        )

        .order_by(LandListing.created_at.desc())

        .all()

    )



    results = []

    for listing in listings:

        owner = db.query(User).filter(User.id == listing.owner_user_id).first()

        kyc = db.query(KYCRecord).filter(KYCRecord.user_id == listing.owner_user_id).first()

        parcel = db.query(LandParcel).filter(LandParcel.id == listing.parcel_id).first() if listing.parcel_id else None

        results.append({

            "listing_id": listing.id,

            "owner": {

                "id": owner.id if owner else listing.owner_user_id,

                "full_name": owner.full_name if owner else "Unknown",

                "organization": owner.organization if owner else None,

                "phone": owner.phone if owner else None,

                "kyc_status": kyc.status if kyc else "UNKNOWN",

                "kyc_verified_at": kyc.reviewed_at.isoformat() if kyc and kyc.reviewed_at else None,

            },

            "land": {

                "title": listing.title,

                "location_label": listing.location_label,

                "lat": listing.lat,

                "lon": listing.lon,

                "area_ha": listing.area_ha,

                "survey_number": parcel.survey_number if parcel else None,

                "plot_number": parcel.plot_number if parcel else None,

                "village": parcel.village if parcel else None,

                "land_verified": parcel.verification_status == "VERIFIED" if parcel else False,

            },

            "lease": {

                "duration_years": listing.lease_duration_years,

                "type": listing.lease_type,

            },

            "carbon_potential": {

                "estimated_annual_credits_tco2": listing.estimated_annual_credits_tco2,

                "estimated_total_credits_tco2": listing.estimated_total_credits_tco2,

                "preliminary_only": listing.preliminary_only,

                "disclaimer": "Preliminary net creditable estimate — not verified issued credits",

            },

            "notes": listing.notes,

        })



    return {"count": len(results), "landowners": results}





@router.get("/listings/{listing_id}")

def listing_detail(

    listing_id: int,

    user: User = Depends(require_company),

    db: Session = Depends(get_db),

):

    listing = db.query(LandListing).filter(LandListing.id == listing_id).first()

    if not listing or not listing.available:

        raise HTTPException(status_code=404, detail="Listing not found")



    kyc = db.query(KYCRecord).filter(KYCRecord.user_id == listing.owner_user_id).first()

    if not kyc or kyc.status != "VERIFIED":

        raise HTTPException(status_code=403, detail="Owner KYC not verified")



    owner = db.query(User).filter(User.id == listing.owner_user_id).first()

    return {

        "listing_id": listing.id,

        "owner_name": owner.full_name if owner else "Unknown",

        "owner_organization": owner.organization if owner else None,

        "lat": listing.lat,

        "lon": listing.lon,

        "area_ha": listing.area_ha,

        "lease_duration_years": listing.lease_duration_years,

        "lease_type": listing.lease_type,

        "estimated_annual_credits_tco2": listing.estimated_annual_credits_tco2,

        "estimated_total_credits_tco2": listing.estimated_total_credits_tco2,

        "preliminary_only": True,

        "notes": listing.notes,

    }





@router.post("/inquiries", status_code=201)

def submit_lease_inquiry(

    body: LeaseInquiryCreate,

    user: User = Depends(require_company),

    db: Session = Depends(get_db),

):

    """Express lease interest in a KYC-verified land listing."""

    listing = db.query(LandListing).filter(

        LandListing.id == body.listing_id,

        LandListing.status == "active",

        LandListing.available == True,

    ).first()

    if not listing:

        raise HTTPException(status_code=404, detail="Listing not found or unavailable")



    kyc = db.query(KYCRecord).filter(KYCRecord.user_id == listing.owner_user_id).first()

    if not kyc or kyc.status != "VERIFIED":

        raise HTTPException(status_code=403, detail="Landowner KYC not verified")



    existing = db.query(LeaseInquiry).filter(

        LeaseInquiry.listing_id == body.listing_id,

        LeaseInquiry.company_user_id == user.id,

        LeaseInquiry.status == "SUBMITTED",

    ).first()

    if existing:

        raise HTTPException(status_code=400, detail="You already have a pending inquiry for this listing")



    inquiry = LeaseInquiry(

        listing_id=body.listing_id,

        company_user_id=user.id,

        message=body.message,

        proposed_lease_years=body.proposed_lease_years,

        status="SUBMITTED",

    )

    db.add(inquiry)

    db.commit()

    db.refresh(inquiry)



    owner = db.query(User).filter(User.id == listing.owner_user_id).first()

    return {

        "message": "Lease inquiry submitted — landowner will respond offline",

        "inquiry_id": inquiry.id,

        "listing_title": listing.title,

        "landowner": owner.full_name if owner else "Unknown",

        "status": inquiry.status,

    }





@router.get("/inquiries")

def my_inquiries(user: User = Depends(require_company), db: Session = Depends(get_db)):

    inquiries = (

        db.query(LeaseInquiry)

        .filter(LeaseInquiry.company_user_id == user.id)

        .order_by(LeaseInquiry.created_at.desc())

        .all()

    )

    results = []

    for inq in inquiries:

        listing = db.query(LandListing).filter(LandListing.id == inq.listing_id).first()

        results.append({

            "id": inq.id,

            "listing_id": inq.listing_id,

            "listing_title": listing.title if listing else None,

            "message": inq.message,

            "proposed_lease_years": inq.proposed_lease_years,

            "status": inq.status,

            "landowner_response": inq.landowner_response,

            "created_at": inq.created_at.isoformat() if inq.created_at else None,

            "responded_at": inq.responded_at.isoformat() if inq.responded_at else None,

        })

    return {"count": len(results), "inquiries": results}


@router.get("/contracts")
def my_contracts(user: User = Depends(require_company), db: Session = Depends(get_db)):
    contracts = (
        db.query(LeaseContract)
        .filter(LeaseContract.company_user_id == user.id)
        .order_by(LeaseContract.created_at.desc())
        .all()
    )
    return {"count": len(contracts), "contracts": [contract_to_dict(c, db) for c in contracts]}


@router.post("/contracts/{contract_id}/sign")
def sign_contract_company(
    contract_id: int,
    body: ContractSign,
    user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    contract = db.query(LeaseContract).filter(
        LeaseContract.id == contract_id,
        LeaseContract.company_user_id == user.id,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.company_signature:
        raise HTTPException(status_code=400, detail="Already signed")

    contract.company_signature = body.typed_name
    contract.company_signed_at = datetime.utcnow()
    if contract.landowner_signature:
        contract.status = "SIGNED"
    else:
        contract.status = "PARTIALLY_SIGNED"
    db.commit()

    generate_contract_pdf(db, contract)
    return {"message": "Contract signed by company", "status": contract.status}


@router.post("/contracts/{contract_id}/pay")
def record_payment(
    contract_id: int,
    body: PaymentRecord,
    user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    contract = db.query(LeaseContract).filter(
        LeaseContract.id == contract_id,
        LeaseContract.company_user_id == user.id,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.status not in ("SIGNED", "PARTIALLY_SIGNED"):
        raise HTTPException(status_code=400, detail="Contract must be signed before payment")
    if contract.payment_status == "PAID":
        raise HTTPException(status_code=400, detail="Already paid")

    contract.payment_amount_inr = body.amount_inr
    contract.payment_reference = body.reference
    contract.payment_status = "PAID"
    contract.paid_at = datetime.utcnow()
    contract.status = "COMPLETED"
    db.commit()

    generate_contract_pdf(db, contract)
    return {"message": "Payment recorded", "status": contract.status, "payment_status": contract.payment_status}


@router.get("/contracts/{contract_id}/pdf")
def download_contract_pdf_company(
    contract_id: int,
    user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    from pathlib import Path as P
    from fastapi.responses import FileResponse
    contract = db.query(LeaseContract).filter(
        LeaseContract.id == contract_id,
        LeaseContract.company_user_id == user.id,
    ).first()
    if not contract or not contract.pdf_path:
        raise HTTPException(status_code=404, detail="Contract PDF not found")
    path = P(contract.pdf_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file missing on server")
    return FileResponse(path, filename=f"lease_contract_{contract.id}.pdf", media_type="application/pdf")


@router.get("/inquiries/{inquiry_id}/messages")
def get_inquiry_messages_company(
    inquiry_id: int,
    user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    inq = db.query(LeaseInquiry).filter(
        LeaseInquiry.id == inquiry_id,
        LeaseInquiry.company_user_id == user.id,
    ).first()
    if not inq:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    messages = (
        db.query(InquiryMessage)
        .filter(InquiryMessage.inquiry_id == inquiry_id)
        .order_by(InquiryMessage.created_at.asc())
        .all()
    )
    return {
        "inquiry_id": inquiry_id,
        "count": len(messages),
        "messages": [
            {
                "id": m.id,
                "sender_user_id": m.sender_user_id,
                "sender_role": m.sender_role,
                "body": m.body,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@router.post("/inquiries/{inquiry_id}/messages", status_code=201)
def send_message_company(
    inquiry_id: int,
    body: MessageCreate,
    user: User = Depends(require_company),
    db: Session = Depends(get_db),
):
    inq = db.query(LeaseInquiry).filter(
        LeaseInquiry.id == inquiry_id,
        LeaseInquiry.company_user_id == user.id,
    ).first()
    if not inq:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    if inq.status not in ("ACCEPTED", "SUBMITTED"):
        raise HTTPException(status_code=400, detail="Messaging only available for active inquiries")

    msg = InquiryMessage(
        inquiry_id=inquiry_id,
        sender_user_id=user.id,
        sender_role="company",
        body=body.body,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"message": "Message sent", "id": msg.id}
