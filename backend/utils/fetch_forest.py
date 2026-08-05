# fetch_forests.py
import requests, json
from pathlib import Path

def fetch_mumbai_forests():
    # Overpass API — fetches real forest/park areas in Mumbai+Thane
    query = """
    [out:json][timeout:60];
    (
      way["landuse"="forest"](18.85,72.75,19.35,73.10);
      way["leisure"="park"](18.85,72.75,19.35,73.10);
      way["natural"="wood"](18.85,72.75,19.35,73.10);
      relation["landuse"="forest"](18.85,72.75,19.35,73.10);
    );
    out body;
    >;
    out skel qt;
    """
    res = requests.post(
        "https://overpass-api.de/api/interpreter",
        data=query, timeout=60
    )
    data = res.json()

    forests = []
    for el in data['elements']:
        if el['type'] == 'way' and 'tags' in el:
            tags = el['tags']
            forests.append({
                "osm_id":   el['id'],
                "name":     tags.get('name', 'Unnamed Forest Area'),
                "type":     tags.get('landuse') or tags.get('leisure') or tags.get('natural'),
                "area_ha":  round(float(tags.get('area', 0)) / 10000, 2),
                "location": "Mumbai/Thane",
                "lat":      tags.get('lat', 19.076),
                "lon":      tags.get('lon', 72.877),
            })

    print(f"Found {len(forests)} real forest/park areas")
    return forests

if __name__ == "__main__":
    forests = fetch_mumbai_forests()
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "real_forests.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(forests, f, indent=2)
    print(f"Saved to {out_file}")