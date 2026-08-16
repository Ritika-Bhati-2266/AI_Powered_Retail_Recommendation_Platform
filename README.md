# AI Powered Retail Recommendation Platform

A production-grade, full-stack e-commerce platform with hyper-personalized product recommendations and segment-based offers. Built with privacy by design — consent-gated, GDPR/DPDP Act compliant, with a live demo mode that requires no signup.

> **Live demo:** [https://retail-hyper.onrender.com](https://retail-hyper.onrender.com)

---

## Architecture

```
┌──────────────────────┐      ┌──────────────────┐
│   React Frontend     │──────▶  FastAPI Backend │
│   (Vite + TS + TW)   │◀──────│  (Python 3.12)  │
└──────────────────────┘      └────────┬─────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
      ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
      │   Postgres   │        │    Redis      │        │  Model File  │
      │  (Events,    │        │  (Cache)      │        │  (joblib)    │
      │   Customers, │        └──────────────┘        └──────────────┘
      │   Products)  │
      └──────────────┘
```

### Components

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS | Customer-facing storefront + admin dashboard with real-time recommendations and offers |
| **API** | FastAPI (async Python) | REST endpoints for events, customers, recommendations, offers, admin, and product search |
| **Database** | SQLAlchemy + asyncpg (PostgreSQL) / aiosqlite (SQLite) | Behavioural events, customer profiles, products, segments, offers, consent logs |
| **Cache** | Redis (optional, gracefully degrades) | Recommendation cache, rate limiting |
| **ML Engine** | scikit-learn TruncatedSVD + cosine similarity | Hybrid collaborative filtering + content-based filtering |

---

## Features

### 1. ML-Powered Hybrid Recommendations
- **Hybrid scoring**: 70% collaborative filtering + 30% content-based similarity
- **Weighted interactions**: Purchases (5x), cart adds (3x), wishlist (2.5x), email clicks (2x), page views (1x)
- **Cold-start support**: New users get recommendations based on signup category preferences
- **Interpretable reason codes** — every recommendation explains why:
  - `purchased_category` — "You previously purchased Electronics items"
  - `viewed_category` — "You've been browsing Clothing"
  - `viewed_product` — "You viewed this item recently"
  - `cart_recovery` — "This item was in your cart"
  - `wishlist_item` — "This item is on your wishlist"
  - `trending_in_segment` — "Popular among similar customers"
  - `top_pick` — "Recommended based on your browsing patterns"
  - `cold_start` — "Based on your interest in [category]"

### 2. Segment-Based Offer Engine
- 8 behavioural segments with hardcoded business rules: `high_value`, `bargain_hunter`, `new_user`, `lapsed`, `cart_abandoner`, `brand_loyalist`, `window_shopper`, `power_user`
- 8 predefined offers targeted to specific segments (e.g., "Welcome 15% Off" for new users, "VIP Exclusive: 25% Off" for high-value customers)
- Automatic offer assignment on customer creation and daily batch refresh
- Currency conversion (USD, INR, EUR, JPY) — prices and discounts convert server-side based on customer preference

### 3. Intelligent Product Search
- Synonym-aware search (e.g., "mobile" matches "smartphone", "tshirt" matches "t-shirt")
- Multi-field matching across product name, brand, and category
- Category filtering with live search-as-you-type

### 4. Privacy & Consent (GDPR / DPDP Act)
- **Consent-gated**: All personalisation requires explicit opt-in
- **Right to forget**: Deletes all behavioural data while keeping a minimal audit record
- **No sensitive attributes**: All features are behavioural only — no age, gender, location, or demographics
- **Audit trail**: Full consent_log with action, regulator (GDPR/DPDP), and timestamp
- **Transparent reason codes**: Every recommendation explains why it was made — no black boxes

### 5. Live Demo Mode
- Browse a full product catalog without any signup
- Search, filter by category, and view product details in an interactive demo
- See the same UI and interaction patterns as the full platform

---

## Quick Start

**Prerequisites:** Python 3.12+, Node.js 18+

### Local Development

#### Backend (Windows — use the helper scripts, recommended)

Do **not** start uvicorn manually in extra terminals — that is what causes duplicated servers and stale processes holding the SQLite file. Use the scripts in `backend/scripts/` instead:

```powershell
# First run only: create the virtualenv + install dependencies
cd backend
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt

# Start the backend (PowerShell)
.\scripts\start_backend.ps1             # default port 8000
.\scripts\start_backend.ps1 -Port 8000  # explicit port
.\scripts\start_backend.ps1 -NoLog      # skip writing logs to backend/logs/
```

`start_backend.ps1` runs three steps (it also shows them as `[1/3]`, `[2/3]`, `[3/3]`):
1. **Stops any existing backend** via `stop_backend.ps1`, so no duplicate server can linger or hold the SQLite file open.
2. **Starts a fresh uvicorn** on port 8000 in a single process (no `--reload` — reload spawns duplicate workers), redirecting output to `backend/logs/backend_out.log` / `backend_err.log`.
3. **Writes the real PID** to `backend/live_pid.txt` and waits for `/api/health` (up to ~30s; first boot may seed data).

To stop the backend:

```powershell
.\scripts\stop_backend.ps1            # default port 8000
.\scripts\stop_backend.ps1 -Port 8000
```

`stop_backend.ps1` kills every process belonging to this backend — anything listening on the target port, any python process running `app.main:app` from this repo, and the stale `live_pid.txt` reference. Use it instead of closing individual terminals to avoid orphan/duplicate processes.

> **Note:** These scripts are Windows/PowerShell only. On macOS / Linux run:
> `source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000`

#### Frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

On first startup, the backend automatically:
1. Creates database tables (SQLite by default — zero-config, no external services needed)
2. Seeds 500 customers, 760 products, and ~10,000 behavioural events
3. Loads a pre-trained ML model if available

### Deploy on Render

The project includes a `render.yaml` for one-click deployment on Render. Set the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/personalisation.db` | PostgreSQL URL for production |
| `REDIS_URL` | (empty) | Redis URL for caching |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/events` | Ingest behaviour event (page_view, purchase, add_to_cart, etc.) |
| `POST` | `/api/customers` | Create a new customer (returns 201) |
| `GET` | `/api/customers/search?q=` | Search customers by name or email |
| `GET` | `/api/customers/by-email?email=` | Lookup customer by email (login) |
| `GET` | `/api/customers/{id}` | Customer profile with metrics + segments |
| `PATCH` | `/api/customers/{id}` | Update customer settings (e.g., currency) |
| `GET` | `/api/customers/{id}/recommendations` | Top 10 personalised recs (consent-gated) |
| `GET` | `/api/customers/{id}/offers` | Active offers for customer |
| `GET` | `/api/customers/{id}/recently-viewed` | Recently viewed products |
| `GET` | `/api/customers/{id}/continue-shopping` | Cart-based continuation suggestions |
| `GET` | `/api/products/search?q=&category=` | Search products (synonym-aware) |
| `GET` | `/api/products/categories` | All product categories |
| `GET` | `/api/products/{id}` | Product detail |
| `GET` | `/api/admin/stats` | System statistics (segment distribution, consent rate) |
| `POST` | `/api/admin/train` | Trigger model training (background) |
| `POST` | `/api/admin/assign-offers` | Re-run offer assignment for all customers |
| `POST` | `/api/admin/right-to-forget/{id}` | GDPR/DPDP right to forget |

---

## Training the Model

Visit the admin dashboard and click **"Train Model"** or call the API directly. Admin endpoints require a valid Bearer token for the seeded admin account (`admin@personalshop.com` / `Customer@2030`):

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@personalshop.com","password":"Customer@2030"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/admin/train \
  -H "Authorization: Bearer $TOKEN"
```

Training runs in the background using scikit-learn's TruncatedSVD. Once complete, recommendations become available for all consenting customers.

---

## Privacy & Compliance

### Consent Flow
1. Customer record has `consent_given` boolean (set during signup)
2. All personalisation endpoints check consent before returning data
3. If consent is revoked, a 403 response is returned immediately
4. Consent actions are logged in `consent_log` with regulator tracking

### Right to Forget
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@personalshop.com","password":"Customer@2030"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/admin/right-to-forget/{customer_id} \
  -H "Authorization: Bearer $TOKEN"
```

This:
- Deletes all behavioural events for the customer
- Removes recommendations, segments, and offers
- Revokes consent
- Logs the action with regulator and timestamp (minimal record kept)

### What We DON'T Do
- No demographic profiling (age, gender, location)
- No sensitive attribute inference
- No third-party data enrichment
- No dark patterns or deceptive personalisation

---

## Project Structure

```
retail-personalisation/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point + lifespan
│   │   ├── config.py             # Settings via env vars
│   │   ├── database.py           # Async SQLAlchemy engine
│   │   ├── models.py             # ORM models (9 tables)
│   │   ├── schemas.py            # Pydantic v2 schemas
│   │   ├── recommender.py        # Hybrid CF + CBF engine (SVD)
│   │   ├── offers.py             # Segment logic + offer assignment
│   │   ├── privacy.py            # Consent service + right to forget
│   │   ├── currency.py           # Currency conversion (USD/INR/EUR/JPY)
│   │   ├── cache.py              # Redis cache helpers
│   │   ├── utils.py              # DB-portable utilities
│   │   ├── seed_data.py          # Synthetic data generator
│   │   └── routers/
│   │       ├── events.py         # Event ingestion
│   │       ├── customers.py      # Customer CRUD + search + profile
│   │       ├── products.py       # Product search with synonyms
│   │       ├── recommendations.py# Personalised recs with cold-start
│   │       ├── offers.py         # Customer offers endpoint
│   │       ├── insights.py       # Recently viewed + continue shopping
│   │       ├── admin.py          # Train, stats, right to forget
│   │       └── mcp/              # OAuth / MCP auth support
│   ├── data/                     # Model checkpoints + SQLite DB
│   ├── scripts/
│   │   ├── start_backend.ps1     # Canonical backend start (kills stale, starts, waits for health)
│   │   └── stop_backend.ps1      # Cleanly stop all backend processes + free the port
│   ├── requirements.txt
│   ├── pytest.ini
│   └── render.yaml
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Main dashboard + routing
│   │   ├── api/client.ts         # API client (fetch-based)
│   │   ├── types.ts              # TypeScript interfaces
│   │   ├── utils/formatPrice.ts  # Price formatting helper
│   │   └── components/
│   │       ├── LoginScreen.tsx    # Landing + login + signup
│   │       ├── CustomerView.tsx   # Customer storefront portal
│   │       ├── DemoView.tsx       # No-signup demo mode
│   │       ├── CustomerSearch.tsx # Admin customer search
│   │       ├── CustomerProfile.tsx# Profile card + metrics grid
│   │       ├── ProductSearch.tsx  # Product catalog with filters
│   │       ├── RecommendationsPanel.tsx # Recs grid + reason badges
│   │       ├── OffersPanel.tsx    # Active offers display
│   │       ├── AnalyticsPage.tsx  # System stats + segment charts
│   │       └── ReasonCodeBadge.tsx# Color-coded reason tags
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
└── README.md
```

---

## Scale Readiness

The system is designed for production scale:

- **500K customers**, **20K SKUs**, **2M events/day**
- **Storage**: PostgreSQL handles this comfortably with proper indexing (composite indexes on `(customer_id, event_type)` and `event_timestamp DESC`)
- **Training**: TruncatedSVD with 50 components trains in minutes at this scale
- **Recommendation serving**: Near-real-time via precomputed recommendations or live model inference
- **Batch cycle**: Daily segment refresh + offer assignment is O(n) in customer count
- **Caching**: Redis caches popular recommendations to reduce DB load
- **Currency conversion**: Server-side with configurable rates, extendable to live forex APIs
