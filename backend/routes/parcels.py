"""Land parcel and biomass analysis API routes."""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

RASTER_DIR = Path(__file__).resolve().parent.parent / "data" / "rasters"

from database import get_db
from models.carbon_assessment import CarbonAssessment
from models.land_parcel import LandParcel
from schemas.parcels import AnalyzeRequest, ParcelCreate
from services.biomass import analyze_parcel
from services.carbon import biomass_to_carbon
from services.geometry import (
    compute_area_ha,
    dumps_geojson,
    geometry_centroid,
    parse_geojson_polygon,
    within_mumbai_region,
)

router = APIRouter(prefix="/api/parcels", tags=["Parcels"])


def _parcel_to_response(p: LandParcel) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "location_label": p.location_label,
        "area_ha": p.area_ha,
        "centroid_lat": p.centroid_lat,
        "centroid_lon": p.centroid_lon,
        "geometry": json.loads(p.geometry_geojson),
        "land_cover_dominant": p.land_cover_dominant,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _assessment_to_response(a: CarbonAssessment, base_url: str = "") -> dict:
    assumptions = json.loads(a.assumptions_json) if a.assumptions_json else {}
    raster_url = None
    if a.raster_path:
        fname = a.raster_path.replace("\\", "/").split("/")[-1]
        raster_url = f"{base_url}/api/parcels/rasters/{fname}"

    return {
        "id": a.id,
        "parcel_id": a.parcel_id,
        "status": a.status,
        "model_name": a.model_name,
        "model_version": a.model_version,
        "mean_agbd": a.mean_agbd,
        "median_agbd": a.median_agbd,
        "min_agbd": a.min_agbd,
        "max_agbd": a.max_agbd,
        "agbd_uncertainty": a.agbd_uncertainty,
        "total_biomass_mg": a.total_biomass_mg,
        "carbon_stock_mgc": a.carbon_stock_mgc,
        "co2e_mg": a.co2e_mg,
        "carbon_fraction_used": a.carbon_fraction_used,
        "valid_pixel_pct": a.valid_pixel_pct,
        "satellite_source": a.satellite_source,
        "observation_date": a.observation_date,
        "ndvi_mean": a.ndvi_mean,
        "evi_mean": a.evi_mean,
        "gedi_footprint_count": a.gedi_footprint_count,
        "assumptions": assumptions,
        "raster_url": raster_url,
        "notes": a.notes,
    }


@router.post("", status_code=201)
def create_parcel(data: ParcelCreate, db: Session = Depends(get_db)):
    try:
        geometry = parse_geojson_polygon(data.geometry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not within_mumbai_region(geometry):
        raise HTTPException(
            status_code=400,
            detail="Parcel must intersect the Mumbai/Thane study region (18.85–19.35°N, 72.75–73.10°E)",
        )

    area_ha = compute_area_ha(geometry)
    if area_ha < 0.01:
        raise HTTPException(status_code=400, detail="Parcel area too small (minimum ~0.01 ha)")

    lat, lon = geometry_centroid(geometry)
    parcel = LandParcel(
        name=data.name,
        owner_id=data.owner_id,
        location_label=data.location_label,
        geometry_geojson=dumps_geojson(geometry),
        area_ha=area_ha,
        centroid_lat=lat,
        centroid_lon=lon,
    )
    db.add(parcel)
    db.commit()
    db.refresh(parcel)
    return {"message": "Parcel registered", "parcel": _parcel_to_response(parcel)}


@router.get("")
def list_parcels(db: Session = Depends(get_db)):
    parcels = db.query(LandParcel).order_by(LandParcel.created_at.desc()).all()
    return [_parcel_to_response(p) for p in parcels]


@router.get("/rasters/{filename}")
def get_raster(filename: str):
    safe = Path(filename).name
    path = RASTER_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="Raster not found")
    return FileResponse(path, media_type="image/png")


@router.get("/{parcel_id}")
def get_parcel(parcel_id: int, db: Session = Depends(get_db)):
    p = db.query(LandParcel).filter(LandParcel.id == parcel_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Parcel not found")

    latest = (
        db.query(CarbonAssessment)
        .filter(CarbonAssessment.parcel_id == parcel_id)
        .order_by(CarbonAssessment.created_at.desc())
        .first()
    )
    result = _parcel_to_response(p)
    if latest:
        result["latest_assessment"] = _assessment_to_response(latest)
    return result


@router.post("/{parcel_id}/analyze", status_code=201)
def analyze_parcel_endpoint(
    parcel_id: int,
    body: AnalyzeRequest = AnalyzeRequest(),
    db: Session = Depends(get_db),
):
    p = db.query(LandParcel).filter(LandParcel.id == parcel_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Parcel not found")

    geometry = json.loads(p.geometry_geojson)
    result = analyze_parcel(geometry, p.id, p.area_ha)

    carbon_data = {}
    if result.get("mean_agbd") is not None:
        carbon_data = biomass_to_carbon(
            result["mean_agbd"],
            p.area_ha,
            carbon_fraction=body.carbon_fraction or 0.47,
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
        assumptions_json=result.get("assumptions_json"),
        raster_path=result.get("raster_path"),
        notes=result.get("notes"),
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    resp = _assessment_to_response(assessment)
    resp["carbon"] = carbon_data
    return {
        "message": f"Analysis {result['status']} for parcel {p.name}",
        "assessment": resp,
    }


@router.get("/{parcel_id}/biomass")
def get_parcel_biomass(parcel_id: int, db: Session = Depends(get_db)):
    a = (
        db.query(CarbonAssessment)
        .filter(CarbonAssessment.parcel_id == parcel_id)
        .order_by(CarbonAssessment.created_at.desc())
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="No biomass assessment found — run POST /analyze first")
    return _assessment_to_response(a)


@router.get("/{parcel_id}/carbon")
def get_parcel_carbon(
    parcel_id: int,
    carbon_fraction: Optional[float] = 0.47,
    db: Session = Depends(get_db),
):
    p = db.query(LandParcel).filter(LandParcel.id == parcel_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Parcel not found")

    a = (
        db.query(CarbonAssessment)
        .filter(CarbonAssessment.parcel_id == parcel_id)
        .order_by(CarbonAssessment.created_at.desc())
        .first()
    )
    if not a or a.mean_agbd is None:
        raise HTTPException(
            status_code=404,
            detail="No AGBD data available — GEDI coverage may be insufficient for this parcel",
        )

    carbon = biomass_to_carbon(a.mean_agbd, p.area_ha, carbon_fraction=carbon_fraction or 0.47)
    return {
        "parcel_id": parcel_id,
        "area_ha": p.area_ha,
        "mean_agbd_mg_ha": a.mean_agbd,
        **carbon,
        "model_name": a.model_name,
        "model_version": a.model_version,
        "observation_date": a.observation_date,
    }


@router.get("/{parcel_id}/satellite")
def get_parcel_satellite(parcel_id: int, db: Session = Depends(get_db)):
    a = (
        db.query(CarbonAssessment)
        .filter(CarbonAssessment.parcel_id == parcel_id)
        .order_by(CarbonAssessment.created_at.desc())
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="No satellite analysis found — run POST /analyze first")

    assumptions = json.loads(a.assumptions_json) if a.assumptions_json else {}
    return {
        "parcel_id": parcel_id,
        "satellite_source": a.satellite_source,
        "observation_date": a.observation_date,
        "ndvi_mean": a.ndvi_mean,
        "evi_mean": a.evi_mean,
        "valid_pixel_pct": a.valid_pixel_pct,
        "scene": assumptions.get("sentinel_scene"),
        "raster_url": _assessment_to_response(a).get("raster_url"),
    }
