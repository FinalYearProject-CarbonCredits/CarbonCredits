"""Sentinel-2 discovery via public STAC catalogs."""

from datetime import datetime, timedelta
from typing import Any

import requests

EARTH_SEARCH_STAC = "https://earth-search.aws.element84.com/v1"
CDSE_STAC = "https://stac.dataspace.copernicus.eu/v1"


def search_sentinel2_scenes(
    bbox: tuple[float, float, float, float],
    max_cloud: float = 30.0,
    limit: int = 5,
    catalog: str = EARTH_SEARCH_STAC,
) -> list[dict[str, Any]]:
    """
    Search Sentinel-2 L2A scenes intersecting bbox.
    bbox: (min_lon, min_lat, max_lon, max_lat)
    """
    start = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "collections": ["sentinel-2-l2a"],
        "bbox": list(bbox),
        "datetime": f"{start}/{end}",
        "query": {"eo:cloud_cover": {"lt": max_cloud}},
        "limit": limit,
        "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
    }

    res = requests.post(f"{catalog}/search", json=payload, timeout=30)
    res.raise_for_status()
    features = res.json().get("features", [])
    return [_normalize_scene(f, catalog) for f in features]


def _normalize_scene(feature: dict[str, Any], catalog: str) -> dict[str, Any]:
    props = feature.get("properties", {})
    assets = feature.get("assets", {})
    return {
        "id": feature.get("id"),
        "datetime": props.get("datetime"),
        "cloud_cover": props.get("eo:cloud_cover"),
        "platform": props.get("platform"),
        "tile": props.get("s2:mgrs_tile"),
        "catalog": catalog,
        "self_href": feature.get("links", [{}])[0].get("href") if feature.get("links") else None,
        "red_asset": assets.get("red", {}).get("href"),
        "nir_asset": assets.get("nir", {}).get("href"),
        "green_asset": assets.get("green", {}).get("href"),
        "visual_asset": assets.get("visual", {}).get("href"),
        "bbox": feature.get("bbox"),
    }


def get_best_scene(bbox: tuple[float, float, float, float]) -> dict[str, Any] | None:
    """Return lowest-cloud Sentinel-2 L2A scene for bbox."""
    scenes = search_sentinel2_scenes(bbox)
    return scenes[0] if scenes else None


def scene_metadata_summary(scene: dict[str, Any] | None) -> dict[str, Any]:
    if not scene:
        return {"available": False, "message": "No low-cloud Sentinel-2 L2A scene found in last 12 months"}
    return {
        "available": True,
        "product_id": scene["id"],
        "observation_date": scene["datetime"],
        "cloud_cover_pct": scene["cloud_cover"],
        "tile": scene["tile"],
        "platform": scene["platform"],
        "source": "Sentinel-2 L2A via Element84 Earth Search STAC",
        "catalog": scene["catalog"],
    }
