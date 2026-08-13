"""Apply lightweight SQLite migrations for new columns."""

from sqlalchemy import inspect, text

from database import engine


def migrate_schema():
    """Add new columns to existing tables without dropping data."""
    inspector = inspect(engine)

    if "land_parcels" in inspector.get_table_names():
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
            ("verified_at", "DATETIME"),
            ("verified_by_admin_id", "INTEGER"),
        ]
        with engine.begin() as conn:
            for col, typedef in additions:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE land_parcels ADD COLUMN {col} {typedef}"))

    if "land_listings" in inspector.get_table_names():
        existing = {c["name"] for c in inspector.get_columns("land_listings")}
        if "parcel_id" not in existing:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE land_listings ADD COLUMN parcel_id INTEGER"))
