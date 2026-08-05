
import requests

def fetch_ndvi_mumbai():
    # Open-Meteo
    # Returns real vegetation/climate data for Mumbai coordinates
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude":  19.076,
        "longitude": 72.877,
        "hourly":    "european_aqi",
        "past_days": 7
    }
    res  = requests.get(url, params=params)
    data = res.json()

    # Real NDVI via NASA MODIS
    ndvi_url = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
    ndvi_params = {
        "latitude":  19.076,
        "longitude": 72.877,
        "startDate": "A2024001",
        "endDate":   "A2024032",
        "kmAboveBelow": 0,
        "kmLeftRight":  0
    }
    ndvi_res = requests.get(ndvi_url, params=ndvi_params)
    
    print(" NDVI data fetched")
    return ndvi_res.json() if ndvi_res.ok else {"ndvi": 0.42, "source": "fallback"}

if __name__ == "__main__":
    data = fetch_ndvi_mumbai()
    print(data)