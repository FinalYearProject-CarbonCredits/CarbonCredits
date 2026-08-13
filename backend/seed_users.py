"""Seed demo users for admin, landowner, and company roles."""

from sqlalchemy.orm import Session

from models.kyc import KYCRecord
from models.land_listing import LandListing
from models.user import User
from services.auth import hash_password


def seed_users(db: Session):
    if db.query(User).count() > 0:
        return

    admin = User(
        email="admin@carbonchain.in",
        password_hash=hash_password("admin123"),
        role="admin",
        full_name="CarbonChain Admin",
        organization="CarbonChain",
        phone="+91-9876543210",
    )
    landowner = User(
        email="landowner@example.com",
        password_hash=hash_password("user123"),
        role="landowner",
        full_name="Rajesh Patil",
        organization="Patil Family Land",
        phone="+91-9812345678",
    )
    landowner2 = User(
        email="sunita@example.com",
        password_hash=hash_password("user123"),
        role="landowner",
        full_name="Sunita Deshmukh",
        organization="Deshmukh Estate",
        phone="+91-9823456789",
    )
    company = User(
        email="company@example.com",
        password_hash=hash_password("company123"),
        role="company",
        full_name="Tata Steel Sustainability",
        organization="Tata Steel Ltd",
        phone="+91-9834567890",
    )
    db.add_all([admin, landowner, landowner2, company])
    db.flush()

    # Verified KYC for Rajesh
    kyc1 = KYCRecord(
        user_id=landowner.id,
        status="VERIFIED",
        full_name="Rajesh Patil",
        phone="+91-9812345678",
        address="Yeoor Hills, Thane West, Maharashtra",
        id_document_ref="AADHAAR-XXXX-1234 (verified offline)",
    )
    # Pending KYC for Sunita
    kyc2 = KYCRecord(
        user_id=landowner2.id,
        status="SUBMITTED",
        full_name="Sunita Deshmukh",
        phone="+91-9823456789",
        address="Ulhasnagar, Thane, Maharashtra",
        id_document_ref="AADHAAR-XXXX-5678",
    )
    db.add_all([kyc1, kyc2])
    db.flush()

    # Demo listing from verified landowner
    listing = LandListing(
        owner_user_id=landowner.id,
        title="Yeoor Hills Forest Block — 45 ha",
        location_label="Thane West, Maharashtra",
        lat=19.233,
        lon=73.001,
        area_ha=45.0,
        lease_duration_years=20,
        lease_type="land_lease",
        available=True,
        estimated_annual_credits_tco2=180.0,
        estimated_total_credits_tco2=3600.0,
        preliminary_only=True,
        status="active",
        notes="Mixed deciduous forest. KYC verified. Available for afforestation carbon project lease.",
    )
    listing2 = LandListing(
        owner_user_id=landowner.id,
        title="SGNP Fringe Parcel — 12 ha",
        location_label="Borivali, Mumbai",
        lat=19.213,
        lon=72.910,
        area_ha=12.0,
        lease_duration_years=15,
        lease_type="land_lease",
        available=True,
        estimated_annual_credits_tco2=72.0,
        estimated_total_credits_tco2=1080.0,
        preliminary_only=True,
        status="active",
        notes="Dense vegetation near Sanjay Gandhi National Park.",
    )
    db.add_all([listing, listing2])
    db.commit()
    print("Seeded demo users: admin@carbonchain.in, landowner@example.com, company@example.com")
