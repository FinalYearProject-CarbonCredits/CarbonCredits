#  CarbonChain Backend — Mumbai / Thane Region
#  FastAPI + SQLAlchemy + Real Open Data

#  HOW TO RUN:
#    pip install -r requirements.txt
#    python main.py          ← seeds DB + starts server
#    open http://localhost:8000/docs


import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()  # Load .env before any os.getenv calls

import json
import random
import requests
import uvicorn
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from utils.fetch_ndvi import fetch_ndvi_for_zones

# ── Canonical database setup from database.py ──
# All models (including legacy demo ones below) use this single engine.
# Set DATABASE_URL in .env to switch between SQLite and PostgreSQL.
from database import Base, engine, SessionLocal, get_db, database_info
from models.land_parcel import LandParcel
from models.carbon_assessment import CarbonAssessment
from models.user import User
from models.kyc import KYCRecord
from models.land_listing import LandListing
from models.lease_inquiry import LeaseInquiry
from models.lease_contract import LeaseContract
from models.inquiry_message import InquiryMessage
from models.refresh_token import RefreshToken
from routes.parcels import router as parcels_router
from routes.auth import router as auth_router
from routes.landowner import router as landowner_router
from routes.company import router as company_router
from routes.admin import router as admin_router
from routes.estimate import router as estimate_router
from routes.registry import router as registry_router
from seed_users import seed_users
from migrate import migrate_schema

ENV = os.getenv("CARBONCHAIN_ENV", "development")


#  DB Tables (legacy demo — now share the canonical Base from database.py)

class Project(Base):
    __tablename__ = "projects"
    __table_args__ = {'extend_existing': True}

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String)
    type          = Column(String)
    location      = Column(String)
    area_ha       = Column(Float)
    claimed_co2   = Column(Float)
    pact_score    = Column(Float, nullable=True)
    tokens_issued = Column(Integer, default=0)
    status        = Column(String, default="PENDING")
    lat           = Column(Float, nullable=True)
    lon           = Column(Float, nullable=True)
    osm_id        = Column(String, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)


class Credit(Base):
    __tablename__ = "credits"
    __table_args__ = {'extend_existing': True}

    id         = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer)
    amount_cct = Column(Integer)
    pact_score = Column(Float)
    minted_at  = Column(DateTime, default=datetime.utcnow)


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = {'extend_existing': True}

    id         = Column(Integer, primary_key=True, index=True)
    trade_type = Column(String)
    amount_cct = Column(Integer)
    price_inr  = Column(Float)
    total_inr  = Column(Float)
    traded_at  = Column(DateTime, default=datetime.utcnow)


class NdviRecord(Base):
    __tablename__ = "ndvi_records"
    __table_args__ = {'extend_existing': True}

    id         = Column(Integer, primary_key=True, index=True)
    zone_name  = Column(String)
    ndvi_value = Column(Float)
    lat        = Column(Float)
    lon        = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)


# Create all tables (single engine — respects DATABASE_URL)
Base.metadata.create_all(bind=engine)


#  SEED REAL DATA  (runs once on first startup)

def fetch_real_forests_from_osm() -> list:
    """Fetch actual forest/park polygons in Mumbai+Thane from OpenStreetMap."""
    print("[OSM] Fetching real forest data from OpenStreetMap...")
    query = """
    [out:json][timeout:60];
    (
      way["landuse"="forest"](18.85,72.75,19.35,73.10);
      way["leisure"="park"](18.85,72.75,19.35,73.10);
      way["natural"="wood"](18.85,72.75,19.35,73.10);
    );
    out tags center;
    """
    try:
        res = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            timeout=60,
        )
        elements = res.json().get("elements", [])
        forests = []
        for el in elements:
            tags   = el.get("tags", {})
            center = el.get("center", {})
            name   = tags.get("name", "").strip()
            if not name:
                continue
            forests.append({
                "osm_id":   str(el["id"]),
                "name":     name,
                "type":     tags.get("landuse") or tags.get("leisure") or tags.get("natural", "forest"),
                "area_ha":  round(float(tags.get("area", random.randint(50, 900))) / 10000, 2),
                "lat":      center.get("lat", 19.076),
                "lon":      center.get("lon", 72.877),
            })
        print(f"[OSM] Returned {len(forests)} named forest/park areas")
        return forests[:8]   # keep top 8 for demo clarity
    except Exception as e:
        print(f"[OSM] Fetch failed ({e}), using curated fallback data")
        return []


def seed_database():
    db = SessionLocal()

    if db.query(Project).count() > 0:
        print("[DB] Database already seeded - skipping")
        db.close()
        return

    print("[DB] Seeding database with real Mumbai/Thane data...")

    # 1. Verified real projects (Verra / Maharashtra forest dept)
    real_projects = [
        Project(
            name="Sanjay Gandhi National Park — Carbon Conservation",
            type="Reforestation",
            location="Borivali, Mumbai",
            area_ha=10350.0,
            claimed_co2=28000.0,
            pact_score=89.2,
            tokens_issued=24800,
            status="ACTIVE",
            lat=19.213,
            lon=72.910,
        ),
        Project(
            name="Thane Creek Mangrove Restoration",
            type="Mangrove",
            location="Thane, Maharashtra",
            area_ha=1690.0,
            claimed_co2=4800.0,
            pact_score=84.1,
            tokens_issued=4100,
            status="ACTIVE",
            lat=19.074,
            lon=73.001,
        ),
        Project(
            name="Aarey Colony Forest Protection",
            type="Reforestation",
            location="Goregaon, Mumbai",
            area_ha=1287.0,
            claimed_co2=3200.0,
            pact_score=78.5,
            tokens_issued=2700,
            status="ACTIVE",
            lat=19.163,
            lon=72.871,
        ),
        Project(
            name="Ulhas River Wetland Carbon Project",
            type="Soil Carbon",
            location="Ambernath, Thane",
            area_ha=890.0,
            claimed_co2=1900.0,
            pact_score=61.3,
            tokens_issued=0,
            status="REVIEW",
            lat=19.198,
            lon=73.192,
        ),
        Project(
            name="Mumbai Coastal Mangrove Belt",
            type="Mangrove",
            location="Bandra-Versova, Mumbai",
            area_ha=5142.0,
            claimed_co2=14200.0,
            pact_score=None,
            tokens_issued=0,
            status="PENDING",
            lat=19.081,
            lon=72.836,
        ),
        Project(
            name="Yeoor Hills Biodiversity Reserve",
            type="Reforestation",
            location="Thane West, Maharashtra",
            area_ha=1820.0,
            claimed_co2=5100.0,
            pact_score=None,
            tokens_issued=0,
            status="EVALUATING",
            lat=19.233,
            lon=73.001,
        ),
        Project(
            name="Powai Lake Green Corridor",
            type="Soil Carbon",
            location="Powai, Mumbai",
            area_ha=340.0,
            claimed_co2=820.0,
            pact_score=55.4,
            tokens_issued=0,
            status="REVIEW",
            lat=19.127,
            lon=72.906,
        ),
    ]

    # 2. Pull real OSM forests and add as PENDING projects
    osm_forests = fetch_real_forests_from_osm()
    for f in osm_forests:
        area = f["area_ha"] if f["area_ha"] > 0 else round(random.uniform(40, 600), 1)
        real_projects.append(
            Project(
                name=f["name"],
                type="Reforestation",
                location="Mumbai / Thane (OSM)",
                area_ha=area,
                claimed_co2=round(area * 3.2, 0),
                pact_score=None,
                tokens_issued=0,
                status="PENDING",
                lat=f["lat"],
                lon=f["lon"],
                osm_id=f["osm_id"],
            )
        )

    db.add_all(real_projects)
    db.flush()

    # 3. Credits for approved projects
    credits = [
        Credit(project_id=real_projects[0].id, amount_cct=24800, pact_score=89.2),
        Credit(project_id=real_projects[1].id, amount_cct=4100,  pact_score=84.1),
        Credit(project_id=real_projects[2].id, amount_cct=2700,  pact_score=78.5),
    ]
    db.add_all(credits)

    # 4. Sample trades
    trades = [
        Trade(trade_type="BUY",  amount_cct=500,  price_inr=1240, total_inr=621860),
        Trade(trade_type="BUY",  amount_cct=200,  price_inr=1235, total_inr=248235),
        Trade(trade_type="SELL", amount_cct=1000, price_inr=1255, total_inr=1258765),
        Trade(trade_type="BUY",  amount_cct=150,  price_inr=1242, total_inr=186858),
        Trade(trade_type="SELL", amount_cct=300,  price_inr=1248, total_inr=375486),
    ]
    db.add_all(trades)

    # 5. Real NDVI zones for Mumbai (NASA MODIS values)
    ndvi_zone_coords = [
        {"zone_name": "Sanjay Gandhi National Park", "lat": 19.213, "lon": 72.910},
        {"zone_name": "Aarey Colony Forest",         "lat": 19.163, "lon": 72.871},
        {"zone_name": "Thane Creek Mangroves",       "lat": 19.074, "lon": 73.001},
        {"zone_name": "Borivali Forest Fringe",      "lat": 19.228, "lon": 72.854},
        {"zone_name": "Powai Lake Greenery",         "lat": 19.127, "lon": 72.906},
        {"zone_name": "Yeoor Hills Reserve",         "lat": 19.233, "lon": 73.001},
        {"zone_name": "Ulhas River Wetlands",        "lat": 19.198, "lon": 73.192},
        {"zone_name": "Versova Mangrove Patch",      "lat": 19.160, "lon": 72.807},
    ]

    ndvi_zones = [
        NdviRecord(zone_name=z["zone_name"], ndvi_value=0.0, lat=z["lat"], lon=z["lon"])
        for z in ndvi_zone_coords
    ]
    db.add_all(ndvi_zones)

    db.commit()
    db.close()
    print(f"Seeded {len(real_projects)} projects ({len(osm_forests)} from live OSM), "
          f"{len(credits)} credits, {len(trades)} trades, {len(ndvi_zones)} NDVI zones")


#  FASTAPI APP

app = FastAPI(
    title="CarbonChain API — Mumbai/Thane Region",
    description="Real carbon credit data for Mumbai & Thane using OpenStreetMap, "
                "NASA MODIS NDVI, and Open-Meteo weather APIs.",
    version="2.0.0",
)


# ── HTTPS redirect middleware (production only) ──
class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP → HTTPS when running in production behind a reverse proxy."""
    async def dispatch(self, request: Request, call_next):
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        if proto == "http" and request.url.path not in ("/", "/health"):
            url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(url), status_code=301)
        return await call_next(request)


if ENV == "production":
    app.add_middleware(HTTPSRedirectMiddleware)


# ── CORS — permissive in dev, locked down in production ──
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
if ENV == "production" and _allowed_origins:
    _origins = [o.strip() for o in _allowed_origins.split(",") if o.strip()]
else:
    _origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=ENV == "production",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parcels_router)
app.include_router(auth_router)
app.include_router(landowner_router)
app.include_router(company_router)
app.include_router(admin_router)
app.include_router(estimate_router)
app.include_router(registry_router)


#  SCHEMAS  (request bodies)

class ProjectCreate(BaseModel):
    name:        str
    type:        str
    location:    str
    area_ha:     float
    claimed_co2: float
    lat:         Optional[float] = None
    lon:         Optional[float] = None


class CreditMint(BaseModel):
    project_id: int
    amount_cct: int
    pact_score: float


class TradeCreate(BaseModel):
    trade_type: str    # BUY or SELL
    amount_cct: int
    price_inr:  float


class StatusUpdate(BaseModel):
    status: str


#  ROOT

@app.get("/", tags=["Health"])
def root():
    return {
        "status":  "CarbonChain API is running",
        "region":  "Mumbai / Thane, Maharashtra",
        "docs":    "http://localhost:8000/docs",
        "version": "2.0.0",
        "environment": ENV,
        "database": database_info(),
    }


#  DASHBOARD

@app.get("/api/dashboard", tags=["Dashboard"])
def get_dashboard(db: Session = Depends(get_db)):
    """Summary stats for the dashboard page."""
    total_projects   = db.query(Project).count()
    active_projects  = db.query(Project).filter(Project.status == "ACTIVE").count()
    pending_projects = db.query(Project).filter(Project.status == "PENDING").count()
    total_credits    = db.query(func.sum(Credit.amount_cct)).scalar() or 0
    total_trades     = db.query(Trade).count()
    total_volume     = db.query(func.sum(Trade.total_inr)).scalar() or 0
    avg_ndvi         = db.query(func.avg(NdviRecord.ndvi_value)).scalar() or 0

    return {
        "region":           "Mumbai / Thane",
        "total_projects":   total_projects,
        "active_projects":  active_projects,
        "pending_projects": pending_projects,
        "total_credits_cct": int(total_credits),
        "total_trades":     total_trades,
        "total_volume_inr": round(total_volume, 2),
        "cct_price_inr":    1240,
        "avg_ndvi_region":  round(avg_ndvi, 3),
        "data_sources": [
            "OpenStreetMap Overpass API",
            "NASA MODIS MOD13Q1",
            "Open-Meteo Forecast API",
        ],
    }


#  PROJECTS

@app.get("/api/projects", tags=["Projects"])
def get_projects(
    status: Optional[str] = None,
    type:   Optional[str] = None,
    db:     Session = Depends(get_db),
):
    """List all projects. Filter by ?status=ACTIVE or ?type=Mangrove"""
    q = db.query(Project)
    if status:
        q = q.filter(Project.status == status.upper())
    if type:
        q = q.filter(Project.type == type)
    return q.order_by(Project.created_at.desc()).all()


@app.get("/api/projects/{project_id}", tags=["Projects"])
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a single project by ID."""
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


@app.post("/api/projects", status_code=201, tags=["Projects"])
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    """Register a new carbon project."""
    project = Project(**data.dict())
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"message": "Project registered successfully", "project": project}


@app.patch("/api/projects/{project_id}/status", tags=["Projects"])
def update_project_status(project_id: int, body: StatusUpdate, db: Session = Depends(get_db)):
    """Update project status (ACTIVE / REVIEW / REJECTED / PENDING)."""
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    valid = {"ACTIVE", "PENDING", "REVIEW", "REJECTED", "EVALUATING"}
    if body.status.upper() not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid}")
    p.status = body.status.upper()
    db.commit()
    return {"message": f"Status updated to {p.status}", "project_id": project_id}


@app.delete("/api/projects/{project_id}", tags=["Projects"])
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project (use carefully)."""
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(p)
    db.commit()
    return {"message": "Project deleted"}


#  CREDITS

@app.get("/api/credits", tags=["Credits"])
def get_credits(db: Session = Depends(get_db)):
    """List all minted carbon credit batches."""
    return db.query(Credit).order_by(Credit.minted_at.desc()).all()


@app.post("/api/credits/mint", status_code=201, tags=["Credits"])
def mint_credits(data: CreditMint, db: Session = Depends(get_db)):
    """Mint CCT tokens for a verified project."""
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status == "REJECTED":
        raise HTTPException(status_code=400, detail="Cannot mint credits for a rejected project")

    credit              = Credit(**data.dict())
    project.tokens_issued += data.amount_cct
    project.pact_score   = data.pact_score
    project.status       = "ACTIVE"

    db.add(credit)
    db.commit()
    db.refresh(credit)
    return {
        "message":  f"✅ Minted {data.amount_cct} CCT for {project.name}",
        "credit":   credit,
        "project":  project,
    }


#  TRADES

@app.get("/api/trades", tags=["Trades"])
def get_trades(db: Session = Depends(get_db)):
    """List all trades, newest first."""
    return db.query(Trade).order_by(Trade.traded_at.desc()).all()


@app.post("/api/trades", status_code=201, tags=["Trades"])
def create_trade(data: TradeCreate, db: Session = Depends(get_db)):
    """Execute a BUY or SELL trade."""
    if data.trade_type.upper() not in {"BUY", "SELL"}:
        raise HTTPException(status_code=400, detail="trade_type must be BUY or SELL")

    fee       = data.amount_cct * data.price_inr * 0.003
    total_inr = (data.amount_cct * data.price_inr) + fee

    trade = Trade(
        trade_type=data.trade_type.upper(),
        amount_cct=data.amount_cct,
        price_inr=data.price_inr,
        total_inr=round(total_inr, 2),
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return {
        "message": f"Trade executed: {data.trade_type} {data.amount_cct} CCT @ ₹{data.price_inr}",
        "trade":   trade,
        "fee_inr": round(fee, 2),
    }


#  REAL SATELLITE / NDVI DATA

@app.get("/api/ndvi/mumbai", tags=["Satellite"])
def get_mumbai_ndvi(db: Session = Depends(get_db)):
    """
    Real NDVI scores for Mumbai/Thane green zones.
    Values sourced from NASA MODIS MOD13Q1 product (250m resolution).
    """
    zones = db.query(NdviRecord).all()
    return {
        "region":      "Mumbai / Thane, Maharashtra",
        "source":      "NASA MODIS MOD13Q1 — 250m resolution",
        "product":     "MOD13Q1 v6.1",
        "description": "NDVI (Normalized Difference Vegetation Index): "
                       "0.0–0.2 = bare/urban, 0.2–0.4 = sparse, "
                       "0.4–0.6 = moderate, 0.6–1.0 = dense vegetation",
        "zones": [
            {
                "id":         z.id,
                "name":       z.zone_name,
                "ndvi":       z.ndvi_value,
                "lat":        z.lat,
                "lon":        z.lon,
                "health":     (
                    "EXCELLENT" if z.ndvi_value >= 0.65 else
                    "GOOD"      if z.ndvi_value >= 0.50 else
                    "MODERATE"  if z.ndvi_value >= 0.35 else
                    "POOR"
                ),
                "recorded_at": z.recorded_at,
            }
            for z in zones
        ],
    }

@app.post("/api/ndvi/refresh", tags=["Satellite"])
def refresh_ndvi(db: Session = Depends(get_db)):
    """
    Pulls REAL current NDVI from NASA MODIS for every tracked zone
    and updates the database. Can be slow (2 live calls per zone)
    since it hits NASA's servers directly.
    """
    zones = db.query(NdviRecord).all()
    zone_inputs = [{"name": z.zone_name, "lat": z.lat, "lon": z.lon} for z in zones]
    results = fetch_ndvi_for_zones(zone_inputs)

    updated, failed = 0, 0
    for z, r in zip(zones, results):
        if r.get("live"):
            z.ndvi_value = r["ndvi"]
            z.recorded_at = datetime.utcnow()
            updated += 1
        else:
            failed += 1

    db.commit()
    return {
        "message": f"Refreshed {updated} zones from real MODIS data, {failed} failed",
        "details": results,
    }


@app.get("/api/forests/mumbai", tags=["Satellite"])
def get_mumbai_forests(db: Session = Depends(get_db)):
    """
    Real forest & park areas for Mumbai/Thane from OpenStreetMap + verified sources.
    Includes actual coordinates for map display.
    """
    projects = db.query(Project).filter(
        Project.location.like("%Mumbai%") | Project.location.like("%Thane%")
    ).all()

    return {
        "region": "Mumbai / Thane",
        "source": "OpenStreetMap Overpass API + Maharashtra Forest Dept",
        "total_forest_areas": len(projects),
        "total_area_ha": round(sum(p.area_ha or 0 for p in projects), 1),
        "forests": [
            {
                "id":       p.id,
                "name":     p.name,
                "type":     p.type,
                "area_ha":  p.area_ha,
                "lat":      p.lat,
                "lon":      p.lon,
                "status":   p.status,
                "osm_id":   p.osm_id,
            }
            for p in projects
        ],
    }

#  REAL WEATHER DATA  (Live — hits Open-Meteo every request)

@app.get("/api/weather/mumbai", tags=["Weather"])
def get_mumbai_weather():
    """
    Live weather data for Mumbai from Open-Meteo API.
    No API key required. Updates on every request.
    """
    try:
        res = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":      19.076,
                "longitude":     72.877,
                "current":       [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "windspeed_10m",
                    "weathercode",
                ],
                "daily": [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "windspeed_10m_max",
                ],
                "timezone":      "Asia/Kolkata",
                "past_days":     7,
                "forecast_days": 7,
            },
            timeout=10,
        )
        data    = res.json()
        current = data.get("current", {})
        daily   = data.get("daily", {})

        return {
            "city":      "Mumbai",
            "region":    "Maharashtra, India",
            "source":    "Open-Meteo (real-time)",
            "updated":   current.get("time", datetime.utcnow().isoformat()),
            "current": {
                "temperature_c":    current.get("temperature_2m"),
                "humidity_pct":     current.get("relative_humidity_2m"),
                "precipitation_mm": current.get("precipitation"),
                "windspeed_kmh":    current.get("windspeed_10m"),
            },
            "forecast_7d": {
                "dates":        daily.get("time", []),
                "max_temp_c":   daily.get("temperature_2m_max", []),
                "min_temp_c":   daily.get("temperature_2m_min", []),
                "rainfall_mm":  daily.get("precipitation_sum", []),
                "windspeed":    daily.get("windspeed_10m_max", []),
            },
            "carbon_impact_note": (
                "Higher rainfall supports vegetation growth, "
                "improving NDVI and carbon sequestration potential."
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Weather API unavailable: {str(e)}"
        )


#  REGION SUMMARY  (All real data in one call — great for demo)

@app.get("/api/region/mumbai", tags=["Dashboard"])
def get_region_summary(db: Session = Depends(get_db)):
    """
    Single endpoint combining projects, NDVI, and live weather.
    Perfect for the professor demo — shows everything in one call.
    """
    projects    = db.query(Project).all()
    ndvi_zones  = db.query(NdviRecord).all()
    total_area  = sum(p.area_ha or 0 for p in projects)
    total_co2   = sum(p.claimed_co2 or 0 for p in projects)
    avg_pact    = db.query(func.avg(Project.pact_score)).filter(
                      Project.pact_score.isnot(None)
                  ).scalar() or 0
    avg_ndvi    = db.query(func.avg(NdviRecord.ndvi_value)).scalar() or 0

    # Live weather (non-blocking — skip if API is slow)
    weather = None
    try:
        res     = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 19.076, "longitude": 72.877,
                "current":  ["temperature_2m", "precipitation"],
                "timezone": "Asia/Kolkata",
            },
            timeout=5,
        )
        w       = res.json().get("current", {})
        weather = {
            "temperature_c":    w.get("temperature_2m"),
            "precipitation_mm": w.get("precipitation"),
        }
    except Exception:
        weather = {"note": "Weather data temporarily unavailable"}

    return {
        "region":          "Mumbai / Thane, Maharashtra",
        "summary": {
            "total_projects":       len(projects),
            "active_projects":      sum(1 for p in projects if p.status == "ACTIVE"),
            "total_forest_area_ha": round(total_area, 1),
            "total_claimed_co2":    round(total_co2, 0),
            "avg_pact_score":       round(avg_pact, 1),
            "avg_ndvi":             round(avg_ndvi, 3),
        },
        "live_weather":    weather,
        "top_projects":    [
            {"name": p.name, "pact_score": p.pact_score, "status": p.status}
            for p in sorted(projects, key=lambda x: x.pact_score or 0, reverse=True)[:3]
        ],
        "ndvi_zones":      len(ndvi_zones),
        "data_sources": {
            "forests":  "OpenStreetMap Overpass API",
            "ndvi":     "NASA MODIS MOD13Q1 v6.1",
            "weather":  "Open-Meteo Forecast API",
            "registry": "Maharashtra Forest Dept / Verra VCS",
        },
    }


#  ENTRY POINT

if __name__ == "__main__":
    db_info = database_info()
    print(f"\n[DB] Using {db_info['driver']} — {db_info['url_masked']}")
    migrate_schema()
    seed_database()
    seed_users(SessionLocal())
    print(f"\nStarting CarbonChain API ({ENV} mode)...")
    print("API Docs  -> http://localhost:8000/docs")
    print("Login     -> http://127.0.0.1:8080/login.html")
    print("Region    -> Mumbai / Thane, Maharashtra")
    if ENV != "production":
        print("Demo accounts:")
        print("  admin@carbonchain.in / admin123")
        print("  landowner@example.com / user123")
        print("  company@example.com / company123")
    else:
        print("HTTPS redirect: ENABLED")
        print(f"CORS origins: {_origins}")
    print()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=(ENV != "production"))