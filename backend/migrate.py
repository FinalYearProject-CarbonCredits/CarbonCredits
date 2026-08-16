"""Apply lightweight migrations for new columns and tables."""

from sqlalchemy import inspect, text

from database import Base, engine, is_postgresql


def migrate_schema():
    """Add new columns to existing tables without dropping data."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "land_parcels" in existing_tables:
        existing = {c["name"] for c in inspector.get_columns("land_parcels")}
        additions = [
            ("owner_user_id", "INTEGER"),
            ("survey_number", "VARCHAR"),
            ("plot_number", "VARCHAR"),
            ("village", "VARCHAR"),
            ("taluka", "VARCHAR"),
            ("district", "VARCHAR"),
            ("document_type", "VARCHAR"),
            ("document_filename", "VARCHAR"),
            ("document_path", "VARCHAR"),
            ("declared_area_document_ha", "FLOAT"),
            ("verification_status", "VARCHAR DEFAULT 'PENDING'"),
            ("admin_notes", "TEXT"),
            ("verified_at", "DATETIME" if not is_postgresql() else "TIMESTAMP"),
            ("verified_by_admin_id", "INTEGER"),
        ]
        with engine.begin() as conn:
            for col, typedef in additions:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE land_parcels ADD COLUMN {col} {typedef}"))

    if "land_listings" in existing_tables:
        existing = {c["name"] for c in inspector.get_columns("land_listings")}
        if "parcel_id" not in existing:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE land_listings ADD COLUMN parcel_id INTEGER"))

    # Ensure new tables exist (lease_contracts, inquiry_messages, refresh_tokens, credit_issuances)
    # These are created via Base.metadata.create_all, but we call it here as safety net
    from models.lease_contract import LeaseContract
    from models.inquiry_message import InquiryMessage
    from models.refresh_token import RefreshToken
    from models.credit_issuance import CreditIssuance

    Base.metadata.create_all(bind=engine)
