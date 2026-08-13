import requests

MODIS_BASE = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
NDVI_SCALE = 0.0001  # MOD13Q1 scale factor


def fetch_modis_ndvi(lat: float, lon: float) -> dict:
    """
    Fetch the most recent real NDVI value for a point from NASA's
    MODIS MOD13Q1 product via the ORNL DAAC web service.
    """
    dates_res = requests.get(
        f"{MODIS_BASE}/dates",
        params={"latitude": lat, "longitude": lon},
        timeout=15,
    )
    dates_res.raise_for_status()
    dates = dates_res.json().get("dates", [])
    if not dates:
        raise ValueError("No MODIS dates available for this location")

    latest = dates[-1]
    modis_date = latest["modis_date"]

    subset_res = requests.get(
        f"{MODIS_BASE}/subset",
        params={
            "latitude": lat,
            "longitude": lon,
            "startDate": modis_date,
            "endDate": modis_date,
            "kmAboveBelow": 0,
            "kmLeftRight": 0,
        },
        timeout=15,
    )
    subset_res.raise_for_status()
    subset = subset_res.json().get("subset", [])

    # Find the NDVI band specifically — the response contains EVI,
    # reflectance, quality flags, and angle bands too, all mixed together.
    ndvi_entry = next(
        (entry for entry in subset if entry.get("band") == "250m_16_days_NDVI"),
        None,
    )
    if not ndvi_entry or not ndvi_entry.get("data"):
        raise ValueError("NDVI band not found in MODIS response")

    raw_value = ndvi_entry["data"][0]

    # MOD13Q1 fill value is -3000; valid range is -2000 to 10000
    if raw_value <= -2000:
        raise ValueError("MODIS returned a fill/no-data pixel (likely cloud cover)")

    ndvi = round(raw_value * NDVI_SCALE, 3)

    return {
        "ndvi": ndvi,
        "calendar_date": ndvi_entry.get("calendar_date"),
        "modis_date": modis_date,
        "source": "NASA MODIS MOD13Q1 (real, ORNL DAAC)",
    }


def fetch_ndvi_for_zones(zones: list) -> list:
    """
    zones: [{"name": str, "lat": float, "lon": float}, ...]
    Returns each zone with real NDVI merged in, or an error flag
    if the live fetch failed for that point.
    """
    results = []
    for z in zones:
        try:
            data = fetch_modis_ndvi(z["lat"], z["lon"])
            results.append({**z, **data, "live": True})
        except Exception as e:
            results.append({**z, "ndvi": None, "live": False, "error": str(e)})
    return results


if __name__ == "__main__":
    # quick manual test — Sanjay Gandhi National Park
    print(fetch_modis_ndvi(19.213, 72.910))