# CarbonChain — Project Context

> **Purpose:** Mumbai / Thane carbon credit marketplace demo with real satellite data where available, role-based portals, and a landowner → verification → listing → company workflow.

**Repo:** https://github.com/FinalYearProject-CarbonCredits/CarbonCredits  
**Last major update:** Verified issuance (Verra/GS + VVB) and AGBD-Lite Random Forest

---

## How to Run

Two terminals are required — **different folders, different commands**:

| | Backend | Frontend |
|---|---------|----------|
| **Folder** | `backend/` | `frontend/` |
| **Command** | `python main.py` | `python -m http.server 8080 --bind 127.0.0.1` |
| **URL** | http://127.0.0.1:8000/docs | http://127.0.0.1:8080/login.html |

**Demo logins:**

| Role | Email | Password | Portal |
|------|-------|----------|--------|
| Admin | admin@carbonchain.in | admin123 | `/admin.html` |
| Landowner | landowner@example.com | user123 | `/landowner.html` |
| Company | company@example.com | company123 | `/company.html` |

---

## What Is Added (Implemented)

### 1. Public demo (`frontend/index.html`)

- Dashboard with project map (Mumbai / Thane forests from OSM seed)
- Live weather ticker (Open-Meteo)
- MODIS NDVI refresh endpoint
- Forest Map tab with parcel draw + biomass analysis (`POST /api/parcels`)
- Calculator, blockchain, and trading tabs (**partially simulated UI**)
- Trade execute wired to `POST /api/trades` (records in SQLite)

### 2. Authentication & roles

| File / area | What |
|-------------|------|
| `backend/routes/auth.py` | Register, login, JWT token, `/me`, refresh, logout |
| `backend/services/auth.py` | bcrypt passwords, JWT, env-based secret, refresh tokens, role guards |
| `backend/models/user.py` | Users: admin, landowner, company |
| `backend/models/refresh_token.py` | Refresh token storage (hashed, revocable) |
| `frontend/login.html` | Portal login |
| `frontend/js/auth.js`, `config.js` | Session, API base URL, role routing, auto-refresh on 401 |

### 3. Landowner portal

| Feature | Backend | Frontend |
|---------|---------|----------|
| Draw boundary + upload deed | `POST /api/landowner/land/register` | `landowner.html` + map draw |
| Server-computed area/centroid | `services/geometry.py` | No manual lat/lon entry |
| My parcels | `GET /api/landowner/land` | Parcel list + analyze button |
| Carbon analysis | `POST /api/landowner/land/{id}/analyze` | NDVI, AGBD-Lite RF, credit potential |
| KYC submit | `POST /api/landowner/kyc/submit` | KYC form |
| Publish listing | `POST /api/landowner/listings` | Requires verified land + KYC |
| Submit for issuance | `POST /api/landowner/listings/{id}/verification/submit` | Verra / Gold Standard workflow |
| Issuance status | `GET /api/landowner/verification` | Timeline + certificate download |
| Lease inquiry inbox | `GET/PATCH /api/landowner/inquiries` | Accept / decline companies |
| Threaded messaging | `GET/POST /api/landowner/inquiries/{id}/messages` | Chat UI with auto-refresh polling |
| Lease contracts | `GET /api/landowner/contracts`, `POST .../sign` | Sign + download PDF |

### 4. Company portal

| Feature | Backend | Frontend |
|---------|---------|----------|
| Browse verified landowners | `GET /api/company/available-landowners` | Cards + map + issuance badge |
| Listing detail | `GET /api/company/listings/{id}` | Includes issuance summary |
| Express lease interest | `POST /api/company/inquiries` | Inquiry button + history |
| Registry serial lookup | `GET /api/registry/credits/{serial}` | Public issued-credit lookup |
| Threaded messaging | `GET/POST /api/company/inquiries/{id}/messages` | Chat UI with auto-refresh polling |
| Lease contracts | `GET /api/company/contracts`, `POST .../sign`, `POST .../pay` | Sign + pay + download PDF |

### 5. Admin portal

| Feature | Backend | Frontend |
|---------|---------|----------|
| Pending land verification | `GET/PATCH /api/admin/land/*` | Document download + verify/reject |
| Pending KYC | `GET/PATCH /api/admin/kyc/*` | Verify / reject |
| Credit issuance queue | `GET/PATCH /api/admin/verification/*` | Assign VVB → verify → issue serial |
| All users | `GET /api/admin/users` | User list |
| Lease inquiries monitor | `GET /api/admin/inquiries` | Inquiry queue |

### 6. Carbon / biomass pipeline

| Service | Role |
|---------|------|
| `services/sentinel.py` | Sentinel-2 L2A via Element84 STAC |
| `services/gedi.py` | GEDI L4A footprint queries |
| `services/biomass.py` | Orchestrates NDVI + GEDI + AGBD-Lite RF |
| `services/agbd_lite.py` | Trained RF on GEDI + Sentinel features when in-parcel GEDI missing |
| `services/agbd_lite_model.json` | Serialized 40-tree forest (hold-out R² ≈ 0.83) |
| `services/carbon.py` | Biomass → carbon stock → CO₂e |
| `services/credit_potential.py` | Preliminary credit range by land type |
| `services/baseline.py` | Baseline, additionality, leakage, buffer |
| `services/historical.py` | ~12-month NDVI change screening |
| `services/land_registration.py` | GeoJSON validation, document upload |

**Public parcel API** (Forest Map tab): `backend/routes/parcels.py`  
**Deprecated:** `POST /api/estimate/point` → 410 Gone (free lat/lon entry removed)

### 7. Database models

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | users | Auth + roles |
| `KYCRecord` | kyc_records | Offline KYC workflow |
| `LandParcel` | land_parcels | Drawn boundary + document metadata |
| `CarbonAssessment` | carbon_assessments | Analysis results per parcel |
| `LandListing` | land_listings | Published land for companies |
| `LeaseInquiry` | lease_inquiries | Company ↔ landowner interest |
| `LeaseContract` | lease_contracts | Contract PDF, e-sign, payment tracking |
| `InquiryMessage` | inquiry_messages | Threaded chat messages |
| `RefreshToken` | refresh_tokens | JWT refresh token rotation |
| `CreditIssuance` | credit_issuances | Verra/GS verification & issuance trail |
| Legacy | projects, credits, trades, ndvi_records | Public demo dashboard |

**Storage:** SQLite (default) or PostgreSQL via `DATABASE_URL` env var  
**Database file:** `backend/carbonchain_mumbai.db` (gitignored, SQLite only)  
**Documents:** `backend/data/documents/` (gitignored)  
**Contracts:** `backend/data/contracts/` (gitignored)  
**NDVI rasters:** `backend/data/rasters/` (gitignored)  
**Backups:** `backend/data/backups/` (gitignored, PostgreSQL only)
**Issuance certificates:** `backend/data/certificates/` (gitignored)

### 8. Seed & migration

- `seed_users.py` — demo admin, landowner, company + sample KYC/listings
- `migrate.py` — lightweight SQLite/PG column migrations
- `scripts/validate_gedi.py` — GEDI coverage sanity check
- `scripts/train_agbd_lite.py` — retrain AGBD-Lite RF → `services/agbd_lite_model.json`
- `scripts/backup_db.py` — PostgreSQL backup with pg_dump + retention

### 9. Data honesty labels

All portal carbon figures start labelled **PRELIMINARY**. After admin records third-party verification and issuance, the listing is marked verified (`preliminary_only=false`) and shows a registry / tracking serial. Disclaimers are returned in API responses.

### 10. Digital lease signing

| Component | Details |
|-----------|--------|
| Contract creation | Auto-generated `DRAFT` when landowner accepts inquiry (`services/contract_service.py`) |
| PDF generation | Full contract PDF via `reportlab` (parties, land, terms, signatures, payment status) |
| E-sign | Both parties type full name to digitally sign (`POST .../contracts/{id}/sign`) |
| Status flow | `DRAFT` → `PARTIALLY_SIGNED` → `SIGNED` → `COMPLETED` |
| Payment recording | Company records UPI/NEFT/cheque ref (`POST .../contracts/{id}/pay`) |
| PDF download | Updated after each sign/pay action (`GET .../contracts/{id}/pdf`) |
| UI | Contract cards in both portals with sign button, payment button, PDF download link |

### 11. Company ↔ landowner messaging

| Component | Details |
|-----------|--------|
| Model | `InquiryMessage` — linked to inquiry, tracks sender role |
| API | `GET/POST /api/{landowner,company}/inquiries/{id}/messages` |
| Chat UI | Threaded chat panel (toggle on inquiry card), auto-refresh every 10 seconds |
| Access control | Both parties can message on `SUBMITTED` or `ACCEPTED` inquiries |

### 12. Production auth

| Component | Details |
|-----------|--------|
| Secret | `CARBONCHAIN_SECRET` from env; crashes on startup if weak/missing in production |
| Refresh tokens | SHA-256 hashed, stored in DB, 7-day expiry, automatic rotation on use |
| Frontend auto-refresh | `apiFetch()` intercepts 401, transparently refreshes token, retries request |
| Logout | Revokes refresh token server-side; `revoke_all_user_tokens()` available |
| HTTPS redirect | Middleware activates when `CARBONCHAIN_ENV=production` (checks `X-Forwarded-Proto`) |
| CORS | `ALLOWED_ORIGINS` env var for production origin whitelist |

### 13. Production database

| Component | Details |
|-----------|--------|
| Dual support | `database.py` reads `DATABASE_URL` — defaults to SQLite, supports PostgreSQL |
| Pool settings | PostgreSQL: `pool_size=10`, `max_overflow=20`, `pool_recycle=1800`, `pool_pre_ping=True` |
| Migrations | `migrate.py` handles PG-specific types (`TIMESTAMP` vs `DATETIME`) |
| Backup | `scripts/backup_db.py` — `pg_dump` with timestamped files and configurable retention |
| Dependencies | `psycopg2-binary` in `requirements.txt` |
| Unified engine | All models (including legacy demo) now share the canonical `database.py` engine |

### 14. Verified carbon credit issuance (Verra / Gold Standard style)

| Component | Details |
|-----------|--------|
| Workflow | `SUBMITTED` → `UNDER_VERIFICATION` (assign VVB) → `VERIFIED` → `ISSUED` (or `REJECTED`) |
| Registries | Verra VCS, Gold Standard — methodology codes validated per registry |
| Third-party VVB | Admin must name the Validation & Verification Body before verification starts |
| Serial | Paste real VCS/GS ID, or auto-generate `CC-TRACK-{VCS\|GS}-IN-MH-{id}-{year}` |
| Listing update | On `ISSUED`, `preliminary_only=false` and credit figures become verified amounts |
| Certificate PDF | Generated on VERIFIED/ISSUED via reportlab |
| Public lookup | `GET /api/registry/credits/{serial}` |
| Honesty | No live Verra/Gold Standard API exists for issuance — this is an audit-trail workflow |

### 15. AGBD-Lite ML model (GEDI + Sentinel)

| Component | Details |
|-----------|--------|
| Algorithm | Random Forest regressor, 40 trees, depth 6 |
| Features | NDVI, EVI, NDVI², EVI², NDVI×EVI, NDVI std, nearby GEDI mean, has-nearby flag |
| Labels | GEDI L4A-style AGBD (Mg/ha) with 20–30% relative uncertainty |
| Hold-out | R² ≈ 0.83, RMSE ≈ 20 Mg/ha (`scripts/train_agbd_lite.py`) |
| Inference | Pure Python tree walk — `services/agbd_lite_model.json` (no sklearn at runtime) |
| Fallback | Original NDVI power-law if the model file is missing |
| Pipeline | In-parcel GEDI used when present; otherwise AGBD-Lite RF (+ nearby GEDI prior) |

---

## What Is Real vs Static (Demo)

### Real (live API or server-computed)

- Weather → Open-Meteo
- Regional NDVI refresh → NASA MODIS
- Sentinel-2 NDVI/EVI → real L2A COG bands
- GEDI AGBD → when footprints exist in parcel (often sparse in urban Mumbai)
- AGBD-Lite RF → trained GEDI-calibrated Sentinel NDVI/EVI model (screening)
- Land area / centroid → geodesic from drawn polygon
- Auth, KYC, listings, inquiries → SQLite
- Dashboard project counts → aggregated from DB

### Static / simulated (demo UI only)

- Hero stats (14.2M tCO₂, ₹847Cr, etc.) → hardcoded HTML
- Chart time series → random `genData()` in `app.js`
- Live activity feed → rotating fake messages
- Blockchain visual chain → simulated (mint partially writes DB)
- Order book / DEX liquidity → static HTML
- CCT price ₹1,240 → hardcoded default
- Project `claimed_co2` → `area × 3.2` heuristic in seed
- PACT evaluation on some projects → demo scores

---

## What Is Yet to Be Added (Not Implemented)

### High priority (product gaps)

> **Completed (moved to Implemented):** Digital lease signing, company ↔ landowner messaging, production auth, production database, verified carbon credit issuance workflow, AGBD-Lite Random Forest (GEDI + Sentinel features).

*(No remaining high-priority product gaps in this list.)*

### MRV & methodology (carbon science)

| Item | Status |
|------|--------|
| Historical carbon stock change (biomass time series) | NDVI trend only (~12 mo) |
| Formal baseline scenario modelling | Heuristic BAU rates in `baseline.py` |
| Additionality proof (documented) | Screening score only |
| Leakage quantification | Fixed 10% deduction |
| Buffer pool | Fixed 15% deduction |
| Methodology selection workflow | Mentioned in API `next_steps` only |
| Field plot validation | Not built |

### Frontend / UX gaps

| Item | Status |
|------|--------|
| Wire all trading UI to backend | Execute trade done; order book still static |
| Real blockchain integration | Simulated UI only |
| Mobile-responsive portal polish | Basic layout only |
| Email alerts (KYC approved, inquiry received) | Not built |
| Admin dashboard analytics | Lists only, no charts |

### Backend / DevOps gaps

| Item | Status |
|------|--------|
| Automated tests | None |
| CI/CD pipeline | None |
| Docker / deployment config | None |
| Rate limiting & API keys | None |
| File storage (S3) for documents | Local filesystem only |
| GEDI HDF5 direct parse | CMR/vector fallback only; often 0 footprints |

### Removed / intentionally blocked

| Item | Reason |
|------|--------|
| `POST /api/estimate/point` | Returns 410 — prevents manual lat/lon bypass of map draw |
| Manual land area entry for analysis | Server computes from polygon only |

---

## End-to-End Workflow (Current)

```
Landowner                    Admin                      Company
    │                          │                           │
    ├─ Draw boundary + doc ──►│ Verify land offline       │
    ├─ Analyze carbon ─────────┤                           │
    ├─ Submit KYC ────────────►│ Verify KYC offline        │
    ├─ Publish listing ────────┤                           │
    │                          │                           ├─ Browse listings
    │◄──── Lease inquiry ──────┼───────────────────────────┤
    ├─ Accept / decline ───────┤                           │
    ├─ Submit for issuance ────►│ Assign VVB → verify → issue│
    │                          ├─ Monitor inquiries         │
```

**Blockers for listing:** land `VERIFIED` + KYC `VERIFIED`  
**Blockers for company view:** owner KYC `VERIFIED` + listing `active`

---

## Key File Map

```
CarbonCredits/
├── PROJECT_CONTEXT.md          ← this file
├── README.md                   ← run instructions
├── backend/
│   ├── main.py                 ← legacy APIs + app entry
│   ├── database.py             ← SQLAlchemy engine
│   ├── migrate.py              ← schema migrations
│   ├── seed_users.py           ← demo accounts
│   ├── models/                 ← DB models (incl. credit_issuance)
│   ├── routes/                 ← API routers (incl. registry.py)
│   ├── services/               ← business + satellite logic + agbd_lite_model.json
│   └── scripts/
│       ├── validate_gedi.py
│       ├── train_agbd_lite.py
│       └── backup_db.py
└── frontend/
    ├── index.html              ← public demo
    ├── login.html              ← portal entry
    ├── landowner.html
    ├── company.html
    ├── admin.html
    └── js/
        ├── config.js           ← API URL (window.API)
        ├── auth.js             ← JWT session helpers
        ├── app.js              ← public demo logic
        ├── landowner.js
        ├── company.js
        └── admin.js
```

---

## Suggested Next Steps (for final-year delivery)

1. **Document methodology choice** (e.g. AR-ACM0003) and map pipeline outputs to MRV requirements — issuance UI now collects registry + methodology.
2. **Add email notification stub** when admin verifies KYC or landowner accepts inquiry.
3. **Add pytest** for auth, land registration geometry, credit_potential math, and issuance status transitions.
4. **Clean public demo UI** — label simulated tabs clearly or wire trading to full backend.
5. **Deploy to PostgreSQL** — set `DATABASE_URL` in `.env`, run `scripts/backup_db.py` on cron.

---

## GitHub Notes

- Pushed to `main` on https://github.com/FinalYearProject-CarbonCredits/CarbonCredits
- **Not committed** (`.gitignore`): `*.db`, `__pycache__/`, `backend/data/`, `.env`
- After clone: `pip install -r backend/requirements.txt`, run both servers, DB seeds on first `python main.py`
