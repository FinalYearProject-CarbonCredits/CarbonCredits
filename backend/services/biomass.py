"""Biomass estimation from real Sentinel-2 imagery and GEDI reference."""

import json
from pathlib import Path
from typing import Any

import numpy as np

from services.agbd_lite import MODEL_NAME as LITE_MODEL, infer_agbd_from_ndvi
from services.gedi import (
    fetch_gedi_footprints_in_bbox,
    fetch_gedi_via_ornl_subset,
    filter_footprints_in_polygon,
    summarize_gedi_agbd,
)
from services.historical import compute_ndvi_change
from services.sentinel import get_best_scene, scene_metadata_summary

try:
    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.warp import transform_bounds
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

RASTER_DIR = Path(__file__).resolve().parent.parent / "data" / "rasters"
RASTER_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "GEDI-L4A + Sentinel-2"
MODEL_VERSION = "1.0.0-mvp"
S2_SCALE = 10000.0  # Sentinel-2 L2A surface reflectance scale factor


def _fetch_cog_window(asset_url: str, bbox_wgs84: tuple[float, float, float, float]) -> np.ndarray | None:
    """Read a window from a Cloud Optimized GeoTIFF, reprojecting WGS84 bbox to raster CRS."""
    if not HAS_RASTERIO or not asset_url:
        return None
    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    try:
        with rasterio.open(asset_url) as src:
            dst_bounds = transform_bounds("EPSG:4326", src.crs, min_lon, min_lat, max_lon, max_lat)
            window = from_bounds(*dst_bounds, src.transform)
            if window.width <= 0 or window.height <= 0:
                return None
            data = src.read(1, window=window, boundless=True, fill_value=0)
            return data.astype(np.float32)
    except Exception:
        return None


def _compute_ndvi_evi_from_scene(scene: dict[str, Any], bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    red = _fetch_cog_window(scene.get("red_asset"), bbox)
    nir = _fetch_cog_window(scene.get("nir_asset"), bbox)

    if red is None or nir is None or red.size == 0:
        return {"ndvi_mean": None, "evi_mean": None, "valid_pixel_pct": 0.0}

    # Scale reflectance (Sentinel-2 L2A COGs store DN values)
    red = np.where(red <= 0, np.nan, red / S2_SCALE)
    nir = np.where(nir <= 0, np.nan, nir / S2_SCALE)

    ndvi = (nir - red) / (nir + red + 1e-6)
    evi = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * red + 1 + 1e-6)

    valid = np.isfinite(ndvi) & (ndvi > -0.2) & (ndvi < 1.0) & (red > 0.01)
    if not valid.any():
        return {"ndvi_mean": None, "evi_mean": None, "valid_pixel_pct": 0.0}

    return {
        "ndvi_mean": round(float(np.nanmean(ndvi[valid])), 4),
        "evi_mean": round(float(np.nanmean(evi[valid])), 4),
        "valid_pixel_pct": round(float(valid.sum() / valid.size * 100), 1),
        "ndvi_array": ndvi,
        "valid_mask": valid,
    }


def _save_ndvi_png(ndvi: np.ndarray, valid_mask: np.ndarray, parcel_id: int) -> str | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    norm = np.zeros_like(ndvi)
    if valid_mask.any():
        norm[valid_mask] = np.clip((ndvi[valid_mask] + 0.2) / 1.2, 0, 1)

    r = (1 - norm) * 139 + norm * 34
    g = (1 - norm) * 90 + norm * 197
    b = (1 - norm) * 43 + norm * 94
    alpha = np.where(valid_mask, 200, 0).astype(np.uint8)
    rgba = np.dstack([np.stack([r, g, b], axis=-1).astype(np.uint8), alpha])

    out_path = RASTER_DIR / f"parcel_{parcel_id}_ndvi.png"
    Image.fromarray(rgba, mode="RGBA").save(out_path)
    return str(out_path)


def analyze_parcel(geometry: dict[str, Any], parcel_id: int, area_ha: float) -> dict[str, Any]:
    """
    Parcel biomass pipeline using real GEDI L4A (AGBD) and Sentinel-2 (NDVI/EVI).
    AGBD values come only from GEDI footprints inside the parcel — not fabricated.
    """
    from services.geometry import geometry_bbox

    bbox = geometry_bbox(geometry, buffer_deg=0.001)
    scene = get_best_scene(bbox)
    sat_meta = scene_metadata_summary(scene)

    veg_stats = {"ndvi_mean": None, "evi_mean": None, "valid_pixel_pct": 0.0}
    raster_path = None

    if scene:
        veg_stats = _compute_ndvi_evi_from_scene(scene, bbox)
        ndvi_arr = veg_stats.pop("ndvi_array", None)
        valid_mask = veg_stats.pop("valid_mask", None)
        if ndvi_arr is not None and valid_mask is not None:
            raster_path = _save_ndvi_png(ndvi_arr, valid_mask, parcel_id)

    gedi_all = fetch_gedi_footprints_in_bbox(bbox, limit=500)
    if not gedi_all:
        gedi_all = fetch_gedi_via_ornl_subset(bbox)

    gedi_inside = filter_footprints_in_polygon(gedi_all, geometry)
    gedi_summary = summarize_gedi_agbd(gedi_inside)
    gedi_nearby = summarize_gedi_agbd(gedi_all)

    agbd_stats = {
        "mean_agbd": gedi_summary["mean_agbd"],
        "median_agbd": gedi_summary["median_agbd"],
        "min_agbd": gedi_summary["min_agbd"],
        "max_agbd": gedi_summary["max_agbd"],
    }

    has_ndvi = veg_stats.get("ndvi_mean") is not None
    has_gedi = gedi_summary["count"] >= 1

    if has_gedi:
        data_source = f"GEDI L4A lidar footprints inside parcel (n={gedi_summary['count']})"
        status = "COMPLETE"
        notes = None
    elif has_ndvi and gedi_nearby["count"] >= 1:
        data_source = (
            f"Sentinel-2 NDVI/EVI + nearby GEDI reference "
            f"(n={gedi_nearby['count']}, mean {gedi_nearby['mean_agbd']} Mg/ha)"
        )
        status = "PARTIAL"
        notes = (
            "No GEDI footprints inside parcel polygon. "
            f"Nearby GEDI mean AGBD: {gedi_nearby['mean_agbd']} Mg/ha (reference only, not parcel estimate). "
            "Draw parcel over forest with GEDI coverage, or install AGBD-Lite model for full inference."
        )
        agbd_stats = {k: None for k in agbd_stats}
    elif has_ndvi:
        lite = infer_agbd_from_ndvi(veg_stats["ndvi_mean"])
        if lite["available"]:
            agbd_stats = {
                "mean_agbd": lite["mean_agbd"],
                "median_agbd": lite["median_agbd"],
                "min_agbd": lite["min_agbd"],
                "max_agbd": lite["max_agbd"],
            }
            uncertainty = lite["agbd_uncertainty"]
            data_source = f"AGBD-Lite NDVI regression ({LITE_MODEL}) — no GEDI footprints in parcel"
            status = "PARTIAL"
            notes = lite["note"]
        else:
            data_source = "Sentinel-2 NDVI/EVI — insufficient GEDI coverage for AGBD"
            status = "PARTIAL"
            notes = lite["note"]
            agbd_stats = {k: None for k in agbd_stats}
            uncertainty = None
    else:
        data_source = "Analysis failed — no satellite or GEDI data"
        status = "FAILED"
        notes = "Could not retrieve Sentinel-2 imagery or GEDI data for this parcel."
        agbd_stats = {k: None for k in agbd_stats}

    assumptions = {
        "disclaimer": (
            "Satellite estimate of existing above-ground biomass/carbon stock. "
            "NOT verified carbon credits. NOT suitable for issuance without "
            "methodology-specific MRV, baseline, additionality, and third-party verification."
        ),
        "agbd_unit": "Mg/ha (megagrams biomass per hectare)",
        "biomass_method": data_source,
        "sentinel_scene": sat_meta,
        "gedi_footprints_in_parcel": gedi_summary["count"],
        "gedi_nearby_count": gedi_nearby["count"],
        "gedi_nearby_mean_agbd": gedi_nearby.get("mean_agbd"),
        "raster_type": "NDVI (Sentinel-2)" if raster_path else None,
    }

    uncertainty = locals().get("uncertainty")
    if uncertainty is None and agbd_stats["mean_agbd"] is not None:
        if gedi_summary["count"] >= 2:
            spread = (agbd_stats["max_agbd"] or 0) - (agbd_stats["min_agbd"] or 0)
            uncertainty = round(spread / 2, 2)
        elif has_ndvi and not has_gedi:
            lite_unc = infer_agbd_from_ndvi(veg_stats.get("ndvi_mean"))
            uncertainty = lite_unc.get("agbd_uncertainty")

    ndvi_change = compute_ndvi_change(bbox, veg_stats.get("ndvi_mean")) if has_ndvi else {"available": False}

    agbd_source = "GEDI_L4A" if has_gedi else ("AGBD_LITE" if agbd_stats.get("mean_agbd") else None)

    return {
        "status": status,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        **agbd_stats,
        "agbd_uncertainty": uncertainty,
        "valid_pixel_pct": veg_stats.get("valid_pixel_pct", 0),
        "satellite_source": sat_meta.get("source"),
        "observation_date": sat_meta.get("observation_date"),
        "ndvi_mean": veg_stats.get("ndvi_mean"),
        "evi_mean": veg_stats.get("evi_mean"),
        "gedi_footprint_count": gedi_summary["count"],
        "agbd_source": agbd_source,
        "ndvi_change": ndvi_change,
        "assumptions_json": json.dumps({**assumptions, "ndvi_change": ndvi_change, "agbd_source": agbd_source}),
        "raster_path": raster_path,
        "area_ha": area_ha,
        "notes": notes,
    }
