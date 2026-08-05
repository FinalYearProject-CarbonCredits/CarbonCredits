
import requests, json
from pathlib import Path

def fetch_mumbai_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":   19.076,
        "longitude":  72.877,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "windspeed_10m_max"
        ],
        "timezone":   "Asia/Kolkata",
        "past_days":  30,
        "forecast_days": 7
    }
    res  = requests.get(url, params=params)
    data = res.json()
    print(f"Got {len(data['daily']['time'])} days of real Mumbai weather")
    return data

if __name__ == "__main__":
    data = fetch_mumbai_weather()
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "real_weather.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved to {out_file}")