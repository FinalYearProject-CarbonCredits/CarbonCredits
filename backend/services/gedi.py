"""GEDI L4A footprint queries for biomass reference data."""

from typing import Any

import requests
from shapely.geometry import Point, shape

GEDI_FINDER_URL = "https://lpdaacsvc.cr.usgs.gov/services/gedifinder"
CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
GEDI_COLLECTION = "C2613265540-LPCLOUD"  # GEDI L4A Footprint Level 4A V2 001


def fetch_gedi_footprints_in_bbox(
    bbox: tuple[float, float, float, float],
    limit: int = 200,
) -> list[dict[str, Any]]:
    """
    Query GEDI L4A footprints in bbox from NASA LP DAAC / CMR.
    bbox: (min_lon, min_lat, max_lon, max_lat)
    """
    footprints = _fetch_from_gedi_finder(bbox, limit)
    if footprints:
        return footprints
    return _fetch_from_cmr_opensearch(bbox, limit)


def _fetch_from_gedi_finder(bbox: tuple[float, float, float, float], limit: int) -> list[dict[str, Any]]:
    min_lon, min_lat, max_lon, max_lat = bbox
    params = {
        "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "product": "GEDI04_A",
        "limit": limit,
    }
    try:
        res = requests.get(GEDI_FINDER_URL, params=params, timeout=45)
        if res.status_code != 200:
            return []
        data = res.json()
    except Exception:
        return []

    items = data if isinstance(data, list) else data.get("results", data.get("data", []))
    footprints = []
    for item in items:
        lat = item.get("lat") or item.get("latitude")
        lon = item.get("lon") or item.get("longitude")
        agbd = item.get("agbd") or item.get("AGBD") or item.get("agbd_t")
        if lat is None or lon is None or agbd is None:
            continue
        agbd_val = float(agbd)
        if agbd_val < 0:
            continue
        footprints.append(
            {
                "lat": float(lat),
                "lon": float(lon),
                "agbd_mg_ha": agbd_val,
                "quality": item.get("quality_flag"),
                "source": "GEDI L4A (NASA LP DAAC GEDI Finder)",
            }
        )
    return footprints


def _fetch_from_cmr_opensearch(bbox: tuple[float, float, float, float], limit: int) -> list[dict[str, Any]]:
    """Search CMR for GEDI L4A granules; extract footprint centroids from metadata links."""
    min_lon, min_lat, max_lon, max_lat = bbox
    params = {
        "collection_concept_id": GEDI_COLLECTION,
        "bounding_box": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "page_size": min(limit, 100),
    }
    try:
        res = requests.get(CMR_GRANULES_URL, params=params, timeout=30)
        res.raise_for_status()
        entries = res.json().get("feed", {}).get("entry", [])
    except Exception:
        return []

    footprints = []
    for entry in entries:
        boxes = entry.get("boxes", [])
        agbd = _parse_agbd_from_granule_title(entry.get("title", ""))
        for box in boxes:
            parts = [float(x) for x in box.split()]
            if len(parts) != 4:
                continue
            # CMR box: west south east north
            west, south, east, north = parts
            lat = (south + north) / 2
            lon = (west + east) / 2
            if agbd is not None:
                footprints.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "agbd_mg_ha": agbd,
                        "granule_id": entry.get("title"),
                        "source": "GEDI L4A granule (CMR metadata)",
                    }
                )
    return footprints


def _parse_agbd_from_granule_title(title: str) -> float | None:
    """GEDI granule titles don't include AGBD — return None; real AGBD needs HDF5 parse."""
    return None


def fetch_gedi_via_ornl_subset(bbox: tuple[float, float, float, float]) -> list[dict[str, Any]]:
    """
    Fallback: query NASA ORNL DAAC GEDI L4A vector service if available.
    Uses the GEDI L4A footprint WFS-like endpoint when LP DAAC finder is down.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    # NASA GEDI public footprint GeoJSON service (UMD mirror)
    url = "https://gedi.umd.edu/data/footprints"
    try:
        res = requests.get(
            url,
            params={"bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}", "limit": 100},
            timeout=30,
        )
        if res.status_code != 200:
            return []
        data = res.json()
        features = data if isinstance(data, list) else data.get("features", [])
        results = []
        for f in features:
            props = f.get("properties", f)
            geom = f.get("geometry", {})
            coords = geom.get("coordinates", [])
            if len(coords) >= 2:
                lon, lat = coords[0], coords[1]
            else:
                lat = props.get("lat")
                lon = props.get("lon")
            agbd = props.get("agbd") or props.get("AGBD")
            if lat and lon and agbd is not None and float(agbd) >= 0:
                results.append(
                    {
                        "lat": float(lat),
                        "lon": float(lon),
                        "agbd_mg_ha": float(agbd),
                        "source": "GEDI L4A (UMD footprint service)",
                    }
                )
        return results
    except Exception:
        return []


def filter_footprints_in_polygon(footprints: list[dict[str, Any]], geometry: dict) -> list[dict[str, Any]]:
    """Keep only GEDI footprints whose center falls inside the parcel polygon."""
    poly = shape(geometry)
    inside = []
    for fp in footprints:
        if fp.get("lat") is None or fp.get("lon") is None:
            continue
        if poly.contains(Point(fp["lon"], fp["lat"])):
            inside.append(fp)
    return inside


def summarize_gedi_agbd(footprints: list[dict[str, Any]]) -> dict[str, Any]:
    values = [f["agbd_mg_ha"] for f in footprints if f.get("agbd_mg_ha") is not None]
    if not values:
        return {"count": 0, "mean_agbd": None, "median_agbd": None, "min_agbd": None, "max_agbd": None}
    values_sorted = sorted(values)
    n = len(values_sorted)
    median = values_sorted[n // 2] if n % 2 else (values_sorted[n // 2 - 1] + values_sorted[n // 2]) / 2
    return {
        "count": n,
        "mean_agbd": round(sum(values) / n, 2),
        "median_agbd": round(median, 2),
        "min_agbd": round(min(values), 2),
        "max_agbd": round(max(values), 2),
    }
