"""Multi-temporal Sentinel-2 NDVI for vegetation change screening."""

from datetime import datetime, timedelta
from typing import Any

import requests

from services.sentinel import EARTH_SEARCH_STAC, _normalize_scene

try:
    import numpy as np
    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.warp import transform_bounds
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

S2_SCALE = 10000.0


def search_scenes_for_period(
    bbox: tuple[float, float, float, float],
    days_ago_start: int,
    days_ago_end: int,
    max_cloud: float = 35.0,
) -> list[dict[str, Any]]:
    """Search Sentinel-2 L2A scenes in a historical window."""
    start = (datetime.utcnow() - timedelta(days=days_ago_end)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (datetime.utcnow() - timedelta(days=days_ago_start)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "collections": ["sentinel-2-l2a"],
        "bbox": list(bbox),
        "datetime": f"{start}/{end}",
        "query": {"eo:cloud_cover": {"lt": max_cloud}},
        "limit": 3,
        "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
    }
    res = requests.post(f"{EARTH_SEARCH_STAC}/search", json=payload, timeout=30)
    res.raise_for_status()
    return [_normalize_scene(f, EARTH_SEARCH_STAC) for f in res.json().get("features", [])]


def _ndvi_from_scene(scene: dict[str, Any], bbox: tuple[float, float, float, float]) -> float | None:
    if not HAS_RASTERIO:
        return None
    red_url = scene.get("red_asset")
    nir_url = scene.get("nir_asset")
    if not red_url or not nir_url:
        return None
    min_lon, min_lat, max_lon, max_lat = bbox
    try:
        with rasterio.open(red_url) as red_src:
            dst_bounds = transform_bounds("EPSG:4326", red_src.crs, min_lon, min_lat, max_lon, max_lat)
            window = from_bounds(*dst_bounds, red_src.transform)
            red = red_src.read(1, window=window, boundless=True, fill_value=0).astype("float32")
        with rasterio.open(nir_url) as nir_src:
            dst_bounds = transform_bounds("EPSG:4326", nir_src.crs, min_lon, min_lat, max_lon, max_lat)
            window = from_bounds(*dst_bounds, nir_src.transform)
            nir = nir_src.read(1, window=window, boundless=True, fill_value=0).astype("float32")
        red = np.where(red <= 0, np.nan, red / S2_SCALE)
        nir = np.where(nir <= 0, np.nan, nir / S2_SCALE)
        ndvi = (nir - red) / (nir + red + 1e-6)
        valid = np.isfinite(ndvi) & (ndvi > -0.2) & (ndvi < 1.0) & (red > 0.01)
        if not valid.any():
            return None
        return round(float(np.nanmean(ndvi[valid])), 4)
    except Exception:
        return None


def compute_ndvi_change(
    bbox: tuple[float, float, float, float],
    current_ndvi: float | None,
    lookback_months: int = 12,
) -> dict[str, Any]:
    """
    Compare current parcel NDVI to best historical scene ~lookback_months ago.
    Returns vegetation change screening metrics (not verified carbon stock change).
    """
    if current_ndvi is None:
        return {"available": False, "message": "Current NDVI unavailable for change analysis"}

    days = lookback_months * 30
    historical = search_scenes_for_period(bbox, days_ago_start=days - 45, days_ago_end=days + 45)
    if not historical:
        return {
            "available": False,
            "message": f"No low-cloud Sentinel-2 scene found ~{lookback_months} months ago",
        }

    past_scene = historical[0]
    past_ndvi = _ndvi_from_scene(past_scene, bbox)
    if past_ndvi is None:
        return {"available": False, "message": "Could not compute historical NDVI for comparison"}

    delta = round(current_ndvi - past_ndvi, 4)
    pct_change = round((delta / past_ndvi) * 100, 2) if past_ndvi else None

    trend = "stable"
    if delta > 0.05:
        trend = "greening"
    elif delta < -0.05:
        trend = "browning"

    return {
        "available": True,
        "lookback_months": lookback_months,
        "current_ndvi": current_ndvi,
        "historical_ndvi": past_ndvi,
        "historical_scene_date": past_scene.get("datetime"),
        "ndvi_delta": delta,
        "ndvi_pct_change": pct_change,
        "vegetation_trend": trend,
        "disclaimer": (
            "NDVI change screening only — not verified carbon stock change. "
            "Biomass change requires multi-temporal biomass model or field plots."
        ),
    }
