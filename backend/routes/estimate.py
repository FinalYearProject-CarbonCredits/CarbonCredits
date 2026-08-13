"""Carbon estimation — only via registered land parcels (no free coordinates)."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/estimate", tags=["Estimation"])


@router.post("/point")
def estimate_at_point_removed():
    raise HTTPException(
        status_code=410,
        detail="Removed: use POST /api/landowner/land/register then POST /api/landowner/land/{id}/analyze. "
               "Location and area must come from map-drawn boundary, not manual coordinates.",
    )


@router.post("/listing")
def create_listing_removed():
    raise HTTPException(
        status_code=410,
        detail="Removed: use POST /api/landowner/listings with a verified parcel_id.",
    )
