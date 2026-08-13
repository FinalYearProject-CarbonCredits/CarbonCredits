"""Pydantic schemas for parcel APIs."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ParcelCreate(BaseModel):
    name: str
    geometry: dict[str, Any] = Field(..., description="GeoJSON Polygon or Feature")
    location_label: Optional[str] = None
    owner_id: Optional[str] = None


class ParcelResponse(BaseModel):
    id: int
    name: str
    location_label: Optional[str]
    area_ha: float
    centroid_lat: Optional[float]
    centroid_lon: Optional[float]
    geometry: dict[str, Any]
    land_cover_dominant: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


class AnalyzeRequest(BaseModel):
    carbon_fraction: Optional[float] = 0.47


class AssessmentResponse(BaseModel):
    id: int
    parcel_id: int
    status: str
    model_name: Optional[str]
    model_version: Optional[str]
    mean_agbd: Optional[float]
    median_agbd: Optional[float]
    min_agbd: Optional[float]
    max_agbd: Optional[float]
    agbd_uncertainty: Optional[float]
    total_biomass_mg: Optional[float]
    carbon_stock_mgc: Optional[float]
    co2e_mg: Optional[float]
    carbon_fraction_used: Optional[float]
    valid_pixel_pct: Optional[float]
    satellite_source: Optional[str]
    observation_date: Optional[str]
    ndvi_mean: Optional[float]
    evi_mean: Optional[float]
    gedi_footprint_count: Optional[int]
    assumptions: Optional[dict[str, Any]]
    raster_url: Optional[str]
    notes: Optional[str]
    disclaimer: str = (
        "Satellite/ML estimate of existing above-ground carbon stock. "
        "NOT verified carbon credits."
    )
