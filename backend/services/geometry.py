"""Geometry utilities for land parcels."""

import json
from typing import Any

from pyproj import Geod
from shapely.geometry import shape, mapping
from shapely.validation import explain_validity

WGS84 = Geod(ellps="WGS84")
MUMBAI_BBOX = (72.75, 18.85, 73.10, 19.35)  # min_lon, min_lat, max_lon, max_lat


def parse_geojson_polygon(geojson: dict[str, Any]) -> dict[str, Any]:
    """Validate GeoJSON polygon and return normalized Feature geometry."""
    if geojson.get("type") == "Feature":
        geometry = geojson.get("geometry")
    elif geojson.get("type") == "FeatureCollection":
        features = geojson.get("features") or []
        if not features:
            raise ValueError("FeatureCollection is empty")
        geometry = features[0].get("geometry")
    else:
        geometry = geojson

    if not geometry:
        raise ValueError("Missing geometry in GeoJSON")

    geom_type = geometry.get("type")
    if geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError(f"Geometry must be Polygon or MultiPolygon, got {geom_type}")

    poly = shape(geometry)
    if not poly.is_valid:
        reason = explain_validity(poly)
        raise ValueError(f"Invalid polygon geometry: {reason}")

    if poly.is_empty:
        raise ValueError("Polygon geometry is empty")

    return geometry


def compute_area_ha(geometry: dict[str, Any]) -> float:
    """Compute geodesic area in hectares for a GeoJSON geometry."""
    poly = shape(geometry)
    if poly.geom_type == "MultiPolygon":
        area_m2 = sum(abs(WGS84.geometry_area_perimeter(g)[0]) for g in poly.geoms)
    else:
        area_m2 = abs(WGS84.geometry_area_perimeter(poly)[0])
    return round(area_m2 / 10_000, 4)


def geometry_centroid(geometry: dict[str, Any]) -> tuple[float, float]:
    """Return (lat, lon) centroid of geometry."""
    poly = shape(geometry)
    c = poly.centroid
    return round(c.y, 6), round(c.x, 6)


def geometry_bbox(geometry: dict[str, Any], buffer_deg: float = 0.002) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) with optional buffer."""
    poly = shape(geometry)
    minx, miny, maxx, maxy = poly.bounds
    return (
        minx - buffer_deg,
        miny - buffer_deg,
        maxx + buffer_deg,
        maxy + buffer_deg,
    )


def within_mumbai_region(geometry: dict[str, Any]) -> bool:
    """Check if geometry intersects the Mumbai/Thane study bbox."""
    poly = shape(geometry)
    min_lon, min_lat, max_lon, max_lat = MUMBAI_BBOX
    region = shape(
        {
            "type": "Polygon",
            "coordinates": [[
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]],
        }
    )
    return poly.intersects(region)


def geojson_to_feature(geometry: dict[str, Any], properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": properties or {},
    }


def dumps_geojson(obj: dict[str, Any]) -> str:
    return json.dumps(obj)
