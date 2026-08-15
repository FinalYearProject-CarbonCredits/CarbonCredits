from datetime import datetime



from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from sqlalchemy.orm import Session



from database import get_db

from models.carbon_assessment import CarbonAssessment

from models.kyc import KYCRecord

from models.land_listing import LandListing

from models.land_parcel import LandParcel

from models.lease_inquiry import LeaseInquiry
from models.user import User
from models.lease_contract import LeaseContract
from models.inquiry_message import InquiryMessage
from schemas.auth import KYCSubmit, LandListingFromParcel, LeaseInquiryRespond, ContractSign, MessageCreate
from services.contract_service import create_contract_from_inquiry, contract_to_dict, generate_contract_pdf

from services.auth import require_roles

from services.biomass import analyze_parcel

from services.carbon import biomass_to_carbon

from services.credit_potential import estimate_credit_potential

from services.geometry import dumps_geojson

from services.land_registration import (

    VALID_DOCUMENT_TYPES,

    parcel_to_dict,

    save_land_document,

    validate_and_parse_geometry,

)



router = APIRouter(prefix="/api/landowner", tags=["Landowner"])



require_landowner = require_roles("landowner")





def _get_or_create_kyc(db: Session, user_id: int) -> KYCRecord:

    kyc = db.query(KYCRecord).filter(KYCRecord.user_id == user_id).first()

    if not kyc:

        kyc = KYCRecord(user_id=user_id, status="NOT_STARTED")

        db.add(kyc)

        db.commit()

        db.refresh(kyc)

    return kyc





@router.post("/land/register", status_code=201)

async def register_land(

    geometry: str = Form(..., description="GeoJSON polygon from map draw — sole source of boundary"),

    survey_number: str = Form(...),

    plot_number: str = Form(...),

    village: str = Form(...),

    taluka: str = Form(...),

    district: str = Form(...),

    document_type: str = Form(...),

    declared_area_document_ha: float = Form(..., gt=0, description="Area written on land document (for admin cross-check)"),

    document: UploadFile = File(..., description="Scan of 7/12, sale deed, or property card"),

    user: User = Depends(require_landowner),

    db: Session = Depends(get_db),

):

    if document_type not in VALID_DOCUMENT_TYPES:

        raise HTTPException(status_code=400, detail=f"document_type must be one of {sorted(VALID_DOCUMENT_TYPES)}")



    parsed = validate_and_parse_geometry(geometry)

    stored_name, stored_path = await save_land_document(document)



    location_label = f"{village}, {taluka}, {district}, Maharashtra"

    parcel = LandParcel(

        name=f"Survey {survey_number} / Plot {plot_number} — {village}",

        owner_id=str(user.id),

        owner_user_id=user.id,

        geometry_geojson=dumps_geojson(parsed["geometry"]),

        area_ha=parsed["area_ha"],

        centroid_lat=parsed["centroid_lat"],

        centroid_lon=parsed["centroid_lon"],

        survey_number=survey_number.strip(),

        plot_number=plot_number.strip(),

        village=village.strip(),

        taluka=taluka.strip(),

        district=district.strip(),

        location_label=location_label,

        document_type=document_type,

        document_filename=document.filename,

        document_path=stored_path,

        declared_area_document_ha=declared_area_document_ha,

        verification_status="PENDING",

    )

    db.add(parcel)

    db.commit()

    db.refresh(parcel)



    result = parcel_to_dict(parcel)

    result["message"] = (

        "Land registered. Area and location computed from your drawn boundary. "

        "Admin will cross-check your uploaded document offline before verification."

    )

    return result





@router.get("/land")

def my_land_parcels(user: User = Depends(require_landowner), db: Session = Depends(get_db)):

    parcels = (

        db.query(LandParcel)

        .filter(LandParcel.owner_user_id == user.id)

        .order_by(LandParcel.created_at.desc())

        .all()

    )

    return [parcel_to_dict(p) for p in parcels]





@router.get("/land/{parcel_id}")

def get_land_parcel(

    parcel_id: int,

    user: User = Depends(require_landowner),

    db: Session = Depends(get_db),

):

    p = db.query(LandParcel).filter(LandParcel.id == parcel_id, LandParcel.owner_user_id == user.id).first()

    if not p:

        raise HTTPException(status_code=404, detail="Land parcel not found")

    data = parcel_to_dict(p)

    data["geometry"] = __import__("json").loads(p.geometry_geojson)

    return data





@router.post("/land/{parcel_id}/analyze")

def analyze_registered_land(

    parcel_id: int,

    project_duration_years: int = 20,

    user: User = Depends(require_landowner),

    db: Session = Depends(get_db),

):

    import json



    p = db.query(LandParcel).filter(LandParcel.id == parcel_id, LandParcel.owner_user_id == user.id).first()

    if not p:

        raise HTTPException(status_code=404, detail="Land parcel not found")



    geometry = json.loads(p.geometry_geojson)

    result = analyze_parcel(geometry, p.id, p.area_ha)



    carbon_data = {}

    if result.get("mean_agbd") is not None:

        carbon_data = biomass_to_carbon(result["mean_agbd"], p.area_ha)



    kyc = db.query(KYCRecord).filter(KYCRecord.user_id == user.id).first()

    potential = estimate_credit_potential(

        area_ha=p.area_ha,

        ndvi_mean=result.get("ndvi_mean"),

        mean_agbd=result.get("mean_agbd"),

        carbon_stock_mgc=carbon_data.get("carbon_stock_mgc"),

        project_duration_years=project_duration_years,

        kyc_verified=kyc.status == "VERIFIED" if kyc else False,

        land_verified=p.verification_status == "VERIFIED",

    )



    assessment = CarbonAssessment(

        parcel_id=p.id,

        status=result["status"],

        model_name=result.get("model_name"),

        model_version=result.get("model_version"),

        mean_agbd=result.get("mean_agbd"),

        median_agbd=result.get("median_agbd"),

        min_agbd=result.get("min_agbd"),

        max_agbd=result.get("max_agbd"),

        agbd_uncertainty=result.get("agbd_uncertainty"),

        total_biomass_mg=carbon_data.get("total_biomass_mg"),

        carbon_stock_mgc=carbon_data.get("carbon_stock_mgc"),

        co2e_mg=carbon_data.get("co2e_mg"),

        carbon_fraction_used=carbon_data.get("carbon_fraction_used"),

        valid_pixel_pct=result.get("valid_pixel_pct"),

        satellite_source=result.get("satellite_source"),

        observation_date=result.get("observation_date"),

        ndvi_mean=result.get("ndvi_mean"),

        evi_mean=result.get("evi_mean"),

        gedi_footprint_count=result.get("gedi_footprint_count"),

        assumptions_json=json.dumps({

            **json.loads(result.get("assumptions_json") or "{}"),

            "credit_potential": potential,

            "parcel_verification_status": p.verification_status,

        }),

        raster_path=result.get("raster_path"),

        notes=result.get("notes"),

    )

    db.add(assessment)

    db.commit()



    return {

        "parcel_id": p.id,

        "verification_status": p.verification_status,

        "computed_area_ha": p.area_ha,

        "centroid": {"lat": p.centroid_lat, "lon": p.centroid_lon},

        "satellite_analysis": {

            "status": result["status"],

            "ndvi_mean": result.get("ndvi_mean"),

            "evi_mean": result.get("evi_mean"),

            "mean_agbd_mg_ha": result.get("mean_agbd"),

            "agbd_source": result.get("agbd_source"),

            "ndvi_change": result.get("ndvi_change"),

        },

        "carbon_stock": carbon_data,

        "credit_potential": potential,

        "baseline_assessment": potential.get("baseline_assessment"),

        "kyc_status": kyc.status if kyc else "NOT_STARTED",

        "disclaimer": potential["disclaimer"],

    }





@router.post("/listings", status_code=201)

def publish_listing(

    data: LandListingFromParcel,

    user: User = Depends(require_landowner),

    db: Session = Depends(get_db),

):

    kyc = db.query(KYCRecord).filter(KYCRecord.user_id == user.id).first()

    if not kyc or kyc.status != "VERIFIED":

        raise HTTPException(status_code=403, detail="KYC verification required before publishing")



    parcel = db.query(LandParcel).filter(

        LandParcel.id == data.parcel_id,

        LandParcel.owner_user_id == user.id,

    ).first()

    if not parcel:

        raise HTTPException(status_code=404, detail="Land parcel not found")

    if parcel.verification_status != "VERIFIED":

        raise HTTPException(

            status_code=403,

            detail="Land document and boundary must be admin-verified before listing",

        )



    existing = db.query(LandListing).filter(

        LandListing.parcel_id == parcel.id,

        LandListing.status == "active",

    ).first()

    if existing:

        raise HTTPException(status_code=400, detail="This land parcel already has an active listing")



    import json

    geometry = json.loads(parcel.geometry_geojson)

    result = analyze_parcel(geometry, parcel.id, parcel.area_ha)

    potential = estimate_credit_potential(

        area_ha=parcel.area_ha,

        ndvi_mean=result.get("ndvi_mean"),

        mean_agbd=result.get("mean_agbd"),

        project_duration_years=data.project_duration_years,

        kyc_verified=True,

        land_verified=True,

    )



    listing = LandListing(

        owner_user_id=user.id,

        parcel_id=parcel.id,

        title=data.title or parcel.name,

        location_label=parcel.location_label,

        lat=parcel.centroid_lat,

        lon=parcel.centroid_lon,

        area_ha=parcel.area_ha,

        lease_duration_years=data.lease_duration_years,

        lease_type=data.lease_type,

        available=True,

        estimated_annual_credits_tco2=potential["net_creditable_annual_tco2e"]["max"],

        estimated_total_credits_tco2=potential["net_creditable_total_tco2e"]["max"],

        preliminary_only=True,

        status="active",

        notes=data.notes,

    )

    db.add(listing)

    db.commit()

    db.refresh(listing)



    return {

        "message": "Listing published from verified land record",

        "listing_id": listing.id,

        "area_ha": parcel.area_ha,

        "lease_duration_years": listing.lease_duration_years,

        "credit_potential": potential,

    }





@router.get("/kyc")

def get_kyc(user: User = Depends(require_landowner), db: Session = Depends(get_db)):

    kyc = _get_or_create_kyc(db, user.id)

    return {

        "user_id": user.id,

        "status": kyc.status,

        "full_name": kyc.full_name,

        "phone": kyc.phone,

        "address": kyc.address,

        "id_document_ref": kyc.id_document_ref,

        "submitted_at": kyc.submitted_at.isoformat() if kyc.submitted_at else None,

        "reviewed_at": kyc.reviewed_at.isoformat() if kyc.reviewed_at else None,

        "admin_notes": kyc.admin_notes,

        "offline_process_note": (

            "Submit identity details here. Admin verifies your identity and land ownership "

            "offline against uploaded land documents before approving KYC."

        ),

    }





@router.post("/kyc/submit")

def submit_kyc(

    data: KYCSubmit,

    user: User = Depends(require_landowner),

    db: Session = Depends(get_db),

):

    kyc = _get_or_create_kyc(db, user.id)

    if kyc.status == "VERIFIED":

        raise HTTPException(status_code=400, detail="KYC already verified")



    kyc.full_name = data.full_name

    kyc.phone = data.phone

    kyc.address = data.address

    kyc.id_document_ref = data.id_document_ref

    kyc.status = "SUBMITTED"

    kyc.submitted_at = datetime.utcnow()

    db.commit()

    return {"message": "KYC submitted — pending offline verification", "status": kyc.status}





@router.get("/listings")

def my_listings(user: User = Depends(require_landowner), db: Session = Depends(get_db)):

    listings = db.query(LandListing).filter(LandListing.owner_user_id == user.id).all()

    return [_listing_dict(l, db) for l in listings]





@router.get("/inquiries")

def my_lease_inquiries(user: User = Depends(require_landowner), db: Session = Depends(get_db)):

    """Lease interest requests from companies on this landowner's listings."""

    listing_ids = [

        l.id for l in db.query(LandListing).filter(LandListing.owner_user_id == user.id).all()

    ]

    if not listing_ids:

        return {"count": 0, "inquiries": []}



    inquiries = (

        db.query(LeaseInquiry)

        .filter(LeaseInquiry.listing_id.in_(listing_ids))

        .order_by(LeaseInquiry.created_at.desc())

        .all()

    )

    results = []

    for inq in inquiries:

        listing = db.query(LandListing).filter(LandListing.id == inq.listing_id).first()

        company = db.query(User).filter(User.id == inq.company_user_id).first()

        results.append({

            "id": inq.id,

            "listing_id": inq.listing_id,

            "listing_title": listing.title if listing else None,

            "company_name": company.full_name if company else "Unknown",

            "company_organization": company.organization if company else None,

            "company_phone": company.phone if company else None,

            "message": inq.message,

            "proposed_lease_years": inq.proposed_lease_years,

            "status": inq.status,

            "landowner_response": inq.landowner_response,

            "created_at": inq.created_at.isoformat() if inq.created_at else None,

            "responded_at": inq.responded_at.isoformat() if inq.responded_at else None,

        })

    return {"count": len(results), "inquiries": results}





@router.patch("/inquiries/{inquiry_id}")

def respond_to_inquiry(

    inquiry_id: int,

    body: LeaseInquiryRespond,

    user: User = Depends(require_landowner),

    db: Session = Depends(get_db),

):

    inq = db.query(LeaseInquiry).filter(LeaseInquiry.id == inquiry_id).first()

    if not inq:

        raise HTTPException(status_code=404, detail="Inquiry not found")



    listing = db.query(LandListing).filter(

        LandListing.id == inq.listing_id,

        LandListing.owner_user_id == user.id,

    ).first()

    if not listing:

        raise HTTPException(status_code=403, detail="Not your listing")



    if inq.status != "SUBMITTED":

        raise HTTPException(status_code=400, detail=f"Inquiry already {inq.status.lower()}")



    inq.status = body.status

    inq.landowner_response = body.landowner_response

    inq.responded_at = datetime.utcnow()

    db.commit()



    contract_info = None

    if body.status == "ACCEPTED":

        try:

            contract = create_contract_from_inquiry(db, inq)

            contract_info = {"contract_id": contract.id, "status": contract.status}

        except Exception as e:

            contract_info = {"error": str(e)}



    return {

        "message": f"Inquiry {body.status.lower()}",

        "inquiry_id": inq.id,

        "status": inq.status,

        "contract": contract_info,

    }





@router.get("/contracts")
def my_contracts(user: User = Depends(require_landowner), db: Session = Depends(get_db)):
    contracts = (
        db.query(LeaseContract)
        .filter(LeaseContract.landowner_user_id == user.id)
        .order_by(LeaseContract.created_at.desc())
        .all()
    )
    return {"count": len(contracts), "contracts": [contract_to_dict(c, db) for c in contracts]}


@router.post("/contracts/{contract_id}/sign")
def sign_contract_landowner(
    contract_id: int,
    body: ContractSign,
    user: User = Depends(require_landowner),
    db: Session = Depends(get_db),
):
    contract = db.query(LeaseContract).filter(
        LeaseContract.id == contract_id,
        LeaseContract.landowner_user_id == user.id,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.landowner_signature:
        raise HTTPException(status_code=400, detail="Already signed")

    contract.landowner_signature = body.typed_name
    contract.landowner_signed_at = datetime.utcnow()
    if contract.company_signature:
        contract.status = "SIGNED"
    else:
        contract.status = "PARTIALLY_SIGNED"
    db.commit()

    generate_contract_pdf(db, contract)
    return {"message": "Contract signed by landowner", "status": contract.status}


@router.get("/contracts/{contract_id}/pdf")
def download_contract_pdf_landowner(
    contract_id: int,
    user: User = Depends(require_landowner),
    db: Session = Depends(get_db),
):
    from pathlib import Path as P
    from fastapi.responses import FileResponse
    contract = db.query(LeaseContract).filter(
        LeaseContract.id == contract_id,
        LeaseContract.landowner_user_id == user.id,
    ).first()
    if not contract or not contract.pdf_path:
        raise HTTPException(status_code=404, detail="Contract PDF not found")
    path = P(contract.pdf_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file missing on server")
    return FileResponse(path, filename=f"lease_contract_{contract.id}.pdf", media_type="application/pdf")


@router.get("/inquiries/{inquiry_id}/messages")
def get_inquiry_messages_landowner(
    inquiry_id: int,
    user: User = Depends(require_landowner),
    db: Session = Depends(get_db),
):
    listing_ids = [l.id for l in db.query(LandListing).filter(LandListing.owner_user_id == user.id).all()]
    inq = db.query(LeaseInquiry).filter(
        LeaseInquiry.id == inquiry_id,
        LeaseInquiry.listing_id.in_(listing_ids),
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
def send_message_landowner(
    inquiry_id: int,
    body: MessageCreate,
    user: User = Depends(require_landowner),
    db: Session = Depends(get_db),
):
    listing_ids = [l.id for l in db.query(LandListing).filter(LandListing.owner_user_id == user.id).all()]
    inq = db.query(LeaseInquiry).filter(
        LeaseInquiry.id == inquiry_id,
        LeaseInquiry.listing_id.in_(listing_ids),
    ).first()
    if not inq:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    if inq.status not in ("ACCEPTED", "SUBMITTED"):
        raise HTTPException(status_code=400, detail="Messaging only available for active inquiries")

    msg = InquiryMessage(
        inquiry_id=inquiry_id,
        sender_user_id=user.id,
        sender_role="landowner",
        body=body.body,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"message": "Message sent", "id": msg.id}


def _listing_dict(l: LandListing, db: Session) -> dict:

    parcel = db.query(LandParcel).filter(LandParcel.id == l.parcel_id).first() if l.parcel_id else None

    return {

        "id": l.id,

        "parcel_id": l.parcel_id,

        "title": l.title,

        "location_label": l.location_label,

        "lat": l.lat,

        "lon": l.lon,

        "area_ha": l.area_ha,

        "lease_duration_years": l.lease_duration_years,

        "lease_type": l.lease_type,

        "available": l.available,

        "estimated_annual_credits_tco2": l.estimated_annual_credits_tco2,

        "estimated_total_credits_tco2": l.estimated_total_credits_tco2,

        "preliminary_only": l.preliminary_only,

        "status": l.status,

        "notes": l.notes,

        "survey_number": parcel.survey_number if parcel else None,

        "plot_number": parcel.plot_number if parcel else None,

        "land_verified": parcel.verification_status == "VERIFIED" if parcel else False,

        "created_at": l.created_at.isoformat() if l.created_at else None,

    }


