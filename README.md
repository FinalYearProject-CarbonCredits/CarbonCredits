# CarbonCredits

## Requirements
- Python 3.11+ (or compatible Python 3.x)
- pip

## Install dependencies
From the project root:

```bash
pip install -r backend/requirements.txt
```

If you need the dependencies individually:

```bash
pip install fastapi uvicorn sqlalchemy requests python-multipart
```

## Backend
Start the backend from the project root:

```bash
python backend/main.py
```

This will seed the database if needed and start the API server on:

- http://localhost:8000
- API docs: http://localhost:8000/docs

## Frontend
The frontend files live in `frontend/`.

Option 1: Use a static file server

```bash
cd frontend
python -m http.server 8080
```

Then open:

- http://127.0.0.1:8080

Option 2: Use VS Code Live Server
- Open `frontend/index.html`
- Start Live Server

## Portal Login (Landowner / Company / Admin)

Open http://127.0.0.1:8080/login.html after starting both servers.

| Role | Email | Password | Portal |
|------|-------|----------|--------|
| Admin | admin@carbonchain.in | admin123 | `/admin.html` |
| Landowner | landowner@example.com | user123 | `/landowner.html` |
| Company | company@example.com | company123 | `/company.html` |

### Landowner flow
1. Login → draw exact land boundary on map + upload land document (7/12, deed, etc.)
2. Admin verifies land offline → run carbon analysis (Sentinel-2 + GEDI or AGBD-Lite fallback)
3. Submit KYC (offline verification by admin)
4. After KYC + land verified → publish listing with lease duration
5. Respond to company lease inquiries (accept/decline)
6. Submit listing for Verra / Gold Standard-style verification → admin assigns a VVB → issue serial

### Company flow
1. Login → browse KYC-verified landowners with verified land
2. View lease duration, area, net creditable carbon potential (PRELIMINARY vs ISSUED)
3. Submit lease inquiry → track landowner response
4. Look up issued credits by registry / tracking serial

### Admin flow
1. Login → review pending land documents and KYC submissions
2. Verify/reject after offline document check
3. Monitor company ↔ landowner lease inquiries
4. Credit issuance queue: assign third-party VVB → record verified tCO₂e → issue serial

## Parcel / AGBD Biomass API

New endpoints for land-parcel biomass analysis (Mumbai/Thane region):

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/parcels` | Register a parcel (GeoJSON polygon) |
| GET | `/api/parcels` | List all parcels |
| GET | `/api/parcels/{id}` | Get parcel + latest assessment |
| POST | `/api/parcels/{id}/analyze` | Run Sentinel-2 + GEDI biomass analysis |
| GET | `/api/parcels/{id}/biomass` | Latest AGBD stats |
| GET | `/api/parcels/{id}/carbon` | Carbon stock estimate (not credits) |
| GET | `/api/parcels/{id}/satellite` | Sentinel-2 scene metadata |
| GET | `/api/parcels/rasters/{filename}` | NDVI raster PNG from analysis |

### Example: register a parcel

```bash
curl -X POST http://localhost:8000/api/parcels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SGNP Test Block",
    "location_label": "Borivali, Mumbai",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [72.905, 19.210], [72.915, 19.210],
        [72.915, 19.218], [72.905, 19.218], [72.905, 19.210]
      ]]
    }
  }'
```

### Example: run analysis

```bash
curl -X POST http://localhost:8000/api/parcels/1/analyze \
  -H "Content-Type: application/json" \
  -d '{"carbon_fraction": 0.47}'
```

> **Note:** AGBD values come from real GEDI L4A footprints when available, or **AGBD-Lite v2** (Random Forest trained on GEDI-calibrated Sentinel-2 NDVI/EVI features) as fallback.
> Analysis includes baseline/additionality screening, historical NDVI change, and net creditable estimates.
> Results are **preliminary estimates** until a listing completes the verification & issuance workflow.

Retrain the AGBD-Lite model:

```bash
cd backend
python scripts/train_agbd_lite.py
```

### GEDI validation script

```bash
cd backend
python scripts/validate_gedi.py
python scripts/validate_gedi.py --bbox 72.9 19.2 73.0 19.25
```

### New portal API endpoints

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/api/company/inquiries` | company | Express lease interest |
| GET | `/api/company/inquiries` | company | My inquiries |
| GET | `/api/landowner/inquiries` | landowner | Inquiries on my listings |
| PATCH | `/api/landowner/inquiries/{id}` | landowner | Accept/decline inquiry |
| GET | `/api/admin/inquiries` | admin | All lease inquiries |
| POST | `/api/landowner/listings/{id}/verification/submit` | landowner | Submit for Verra/GS verification |
| GET | `/api/landowner/verification` | landowner | My issuance records |
| GET | `/api/admin/verification/pending` | admin | Issuance queue |
| PATCH | `/api/admin/verification/{id}` | admin | Assign VVB / verify / issue |
| GET | `/api/registry/credits/{serial}` | public | Look up issued serial |

### Additional dependencies

```bash
pip install shapely pyproj numpy rasterio Pillow
```


"# CarbonCredits2" 
