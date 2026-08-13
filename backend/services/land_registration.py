"""Land document storage and registration validation."""

import json
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

from services.geometry import (
    compute_area_ha,
    dumps_geojson,
    geometry_centroid,
    parse_geojson_polygon,
    within_mumbai_region,
)

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

VALID_DOCUMENT_TYPES = {
    "7_12_extract",
    "sale_deed",
    "mutation_entry",
    "survey_settlement",
    "property_card",
    "other",
}


def validate_and_parse_geometry(geometry_json: str) -> dict[str, Any]:
    try:
        geo_input = json.loads(geometry_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid geometry JSON")

    geometry = parse_geojson_polygon(geo_input)
    if not within_mumbai_region(geometry):
        raise HTTPException(
            status_code=400,
            detail="Land boundary must be within Mumbai/Thane region (18.85–19.35°N, 72.75–73.10°E)",
        )

    area_ha = compute_area_ha(geometry)
    if area_ha < 0.05:
        raise HTTPException(status_code=400, detail="Drawn boundary too small (minimum ~0.05 ha / 500 m²)")
    if area_ha > 5000:
        raise HTTPException(status_code=400, detail="Drawn boundary exceeds maximum (5000 ha)")

    lat, lon = geometry_centroid(geometry)
    return {
        "geometry": geometry,
        "area_ha": area_ha,
        "centroid_lat": lat,
        "centroid_lon": lon,
    }


async def save_land_document(file: UploadFile) -> tuple[str, str]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Land document file is required")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Document must be PDF or image ({', '.join(sorted(ALLOWED_EXTENSIONS))})",
        )

    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="Document file too large (max 10 MB)")
    if len(content) < 1024:
        raise HTTPException(status_code=400, detail="Document file appears empty or corrupt")

    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(file.filename).stem)[:60]
    stored_name = f"{uuid.uuid4().hex}_{safe_name}{ext}"
    dest = DOCS_DIR / stored_name
    dest.write_bytes(content)
    return stored_name, str(dest)


def area_mismatch_pct(computed_ha: float, declared_ha: float | None) -> float | None:
    if declared_ha is None or declared_ha <= 0:
        return None
    return round(abs(computed_ha - declared_ha) / declared_ha * 100, 1)


def parcel_to_dict(p) -> dict[str, Any]:
    mismatch = area_mismatch_pct(p.area_ha, p.declared_area_document_ha)
    return {
        "id": p.id,
        "name": p.name,
        "verification_status": p.verification_status,
        "area_ha": p.area_ha,
        "centroid_lat": p.centroid_lat,
        "centroid_lon": p.centroid_lon,
        "survey_number": p.survey_number,
        "plot_number": p.plot_number,
        "village": p.village,
        "taluka": p.taluka,
        "district": p.district,
        "document_type": p.document_type,
        "document_filename": p.document_filename,
        "declared_area_document_ha": p.declared_area_document_ha,
        "area_mismatch_pct": mismatch,
        "area_mismatch_flag": mismatch is not None and mismatch > 15,
        "admin_notes": p.admin_notes,
        "location_label": p.location_label,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "verified_at": p.verified_at.isoformat() if p.verified_at else None,
    }
