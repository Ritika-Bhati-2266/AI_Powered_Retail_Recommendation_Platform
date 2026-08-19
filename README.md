# AI Powered Retail Recommendation Platform

A production-grade, full-stack e-commerce platform with hyper-personalized product recommendations and segment-based offers. Built with privacy by design — consent-gated, GDPR/DPDP Act compliant, with a live demo mode that requires no signup.

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
| **Lint / Quality** | ruff (backend via `backend/pyproject.toml`), `tsc -b` + Vite build (frontend) | `ruff check app` passes clean; frontend type-checks and builds |

---

## Features

### 1. ML-Powered Hybrid Recommendations
- **Hybrid scoring**: 70% collaborative filtering + 30% content-based similarity
- **Weighted interactions**: Purchases (5x), cart adds (3x), wishlist (2.5x), email clicks (2x), page views (1x)
- **Cold-start support**: New users get recommendations based on signup category preferences
- **Live SVD projection for unknown customers**: a customer who joined *after* the last model snapshot (or has events not covered by it) is folded into the trained latent space at inference time by projecting their own interaction vector — so brand-new customers still get personalised collaborative + content recs instead of a generic popular list. There is **no silent fallback to global popularity for customers with behaviour**.
- **Behavior-aware fallback**: if no model signal exists at all, recommendations are biased toward the categories the customer actually browses/buys (recent-event categories, weighted by event type) rather than a flat global "popular" list.
- **Source flag on every response**: `source` reports *why* a recommendation was produced for debugging — `svd` (model matrix or live projection), `cold_start` (category-aware fallback), or `popular` (global last resort).
- **Interpretable reason codes** — every recommendation explains why:
  - `purchased_category` — "You previously purchased Electronics items"
  - `viewed_category` — "You've been browsing Clothing"
  - `viewed_product` — "You viewed this item recently"
  - `cart_recovery` — "This item was in your cart"
  - `wishlist_item` — "This item is on your wishlist"
  - `trending_in_segment` — "Popular among similar customers"
  - `top_pick` — "Recommended based on your browsing patterns"
  - `svd_personalized` — "Recommended based on your shopping history" (SVD-driven default)
  - `cold_start_category_based` — "Based on your browsing in [category]" (behavior-aware fallback)
  - `cold_start` — "Based on your interest in [category]" (signup preferences)
  - `trending` / `popular` — global popularity, only for customers with no behavioural signal

### 2. Segment-Based Offer Engine
- 8 behavioural segments with hardcoded business rules: `high_value`, `bargain_hunter`, `new_user`, `lapsed`, `cart_abandoner`, `brand_loyalist`, `window_shopper`, `power_user`
- 8 predefined offers targeted to specific segments (e.g., "Welcome 15% Off" for new users, "VIP Exclusive: 25% Off" for high-value customers)
- Automatic offer assignment on customer creation and daily batch refresh
- **Individualized offers**: each customer's discount percentage and reason are computed from their own behaviour metrics (LTV, cart-abandon rate, engagement) — a dynamic **5–30%** band per offer
- **Refresh cadence (honest)**: segments are re-evaluated on every event ingest — **non-blocking**: the ingest endpoint persists the event and returns immediately, scheduling the segment recompute as a FastAPI `BackgroundTask` on the same process so request latency isn't paid for the metrics queries and segment writes. Offers are (re)assigned at startup and via `POST /api/admin/assign-offers`. There is still **no background scheduler** and no distributed queue — `BackgroundTasks` is an in-process convenience, not a task broker, so a production deployment should move segmentation, offer assignment and model retraining into a scheduled async job (e.g. APScheduler/Celery with a queue) instead of the synchronous request path described below.
- Currency conversion (USD, INR, EUR, JPY) — prices and discounts convert server-side based on customer preference

### 3. Intelligent Product Search
- Synonym-aware search (e.g., "mobile" matches "smartphone", "tshirt" matches "t-shirt")
- Multi-field matching across product name, brand, and category
- Category filtering with live search-as-you-type

### 4. Privacy & Consent (GDPR / DPDP Act)
- **Consent-gated**: All personalisation requires explicit opt-in
- **Right to forget**: Deletes behavioural data and category preferences, anonymises order PII, and keeps only a minimal compliance record
- **Data export**: Customers can download a complete copy of their behavioural data (GDPR access rights / DPDP)
- **No sensitive attributes**: All features are behavioural only — no age, gender, location, or demographics
- **Audit trail**: Full consent_log with action, regulator (GDPR/DPDP), and timestamp
- **Transparent reason codes**: Every recommendation explains why it was made — no black boxes

### 5. Security Hardening
- **Environment-based secrets**: JWT `SECRET_KEY` is read from the environment (no hardcoded production secrets)
- **Restricted CORS allowlist**: defaults to local dev origins only (not `*`); extend `CORS_ORIGINS` in the environment if you need additional origins
- **bcrypt password hashing** with tunable cost — no plaintext credentials are stored
- **Bearer token is the source of identity**: `X-User-Email`-style headers are never trusted; every owner-scoped route re-verifies the token
- **Role enforcement**: admin-only endpoints re-check the authenticated customer's role (no client-asserted role)
- **Login rate limiting**: credential attempts are throttled per IP + email (5 attempts / 15 min → `429`). The limiter is in-memory for the demo; a production deployment must swap it for the Redis-backed limiter (the Redis integration point is already wired) or a distributed store like `slowapi`
- **Startup guards**: in production, the app fails closed if `SECRET_KEY` is missing or falls back to the dev default, and warns loudly if `DEMO_PASSWORD` is left at the seeded default

### 6. Live Demo Mode
- Browse the **full live product catalog** (760 products) with **no signup** — the demo loads the same backend-seeded catalog the full app uses. There is no separate mock demo data path; the catalog itself is server-generated for this demo/prototype (`backend/app/seed_data.py`) rather than pulled from a third-party product API.
- Instant client-side search across product name, brand, and category
- Open an interactive product-detail modal from any card
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

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/events` | Ingest behaviour event (page_view, purchase, add_to_cart, etc.) |
| `POST` | `/api/customers` | Create a new customer (returns 201) |
| `GET` | `/api/customers/search?q=` | Search customers by name or email |
| `GET` | `/api/customers/by-email?email=` | Admin-only customer lookup by email |
| `GET` | `/api/customers/{id}` | Customer profile with metrics + segments |
| `PATCH` | `/api/customers/{id}` | Update customer settings (e.g., currency) |
| `GET` | `/api/customers/{id}/recommendations` | Top 10 personalised recs (consent-gated) |
| `GET` | `/api/customers/{id}/offers` | Active offers for customer |
| `GET` | `/api/customers/{id}/recently-viewed` | Recently viewed products |
| `GET` | `/api/customers/{id}/continue-shopping` | Cart-based continuation suggestions |
| `GET` | `/api/products/search?q=&category=` | Search products (synonym-aware) |
| `GET` | `/api/products/categories` | All product categories |
| `GET` | `/api/products/{id}` | Product detail |
| `GET` | `/api/customers/{id}/data-export` | Right of access — download all held data (owner) |
| `POST` | `/api/customers/{id}/forget` | Self-service right to forget — erase my data (owner) |
| `GET` | `/api/admin/stats` | System statistics (segment distribution, consent rate) |
| `POST` | `/api/admin/train` | Trigger model training (background) |
| `POST` | `/api/admin/assign-offers` | Re-run offer assignment for all customers |
| `POST` | `/api/admin/right-to-forget/{id}` | GDPR/DPDP right to forget |

---

## Training the Model

Visit the admin dashboard and click **"Train Model"** or call the API directly. Admin endpoints require a valid Bearer token for the seeded admin account. The admin account and its password are created by the seed script (`backend/app/seed_data.py`) using `DEMO_PASSWORD` from the environment (see `backend/.env.example`):

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@personalshop.com","password":"'"$DEMO_PASSWORD"'"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/admin/train \
  -H "Authorization: Bearer $TOKEN"
```

> **Security note:** the seeded admin/demo password (`DEMO_PASSWORD`, currently `Customer@2030`) is **not a secret** — it ships with the repo and is documented. In any shared or production environment you **must** override `DEMO_PASSWORD` via the environment immediately and rotate the account password. Never treat the default demo credentials as real access control.

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
  -d '{"email":"admin@personalshop.com","password":"'"$DEMO_PASSWORD"'"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/admin/right-to-forget/{customer_id} \
  -H "Authorization: Bearer $TOKEN"
```

This:
- Deletes all behavioural events for the customer
- Removes recommendations, segments, and offers
- Revokes consent
- Anonymizes the account (name and password removed, email replaced with an unrouteable placeholder), so the original email can be used for a fresh signup
- Logs the action with regulator and timestamp (minimal audit record kept)

### What We DON'T Do
- No demographic profiling (age, gender, location)
- No sensitive attribute inference
- No third-party data enrichment
- No dark patterns or deceptive personalisation
- Payment is **simulated** — checkout records an order but no real card, wallet, or gateway is charged. This is a demo, not a store.

---

## Project Structure

```
retail-personalisation/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point + lifespan
│   │   ├── config.py             # Settings via env vars (.env support)
│   │   ├── database.py           # Async SQLAlchemy engine
│   │   ├── models.py             # ORM models (9 tables)
│   │   ├── schemas.py            # Pydantic v2 schemas
│   │   ├── recommender.py        # Hybrid CF + CBF engine (SVD)
│   │   ├── offers.py             # Segment logic + individualized offer engine
│   │   ├── privacy.py            # Consent service + right to forget
│   │   ├── currency.py           # Currency conversion (USD/INR/EUR/JPY)
│   │   ├── cache.py              # Redis cache helpers
│   │   ├── utils.py              # DB-portable utilities
│   │   ├── security.py           # bcrypt hashing + bearer-token auth
│   │   ├── serializers.py        # Shared product/response serialization
│   │   ├── seed_data.py          # Synthetic data generator
│   │   ├── routers/
│   │   │   ├── auth.py           # Login + token issuance
│   │   │   ├── events.py         # Event ingestion
│   │   │   ├── customers.py      # Customer CRUD + search + profile
│   │   │   ├── products.py       # Product search with synonyms
│   │   │   ├── recommendations.py# Personalised recs with cold-start
│   │   │   ├── offers.py         # Customer offers endpoint
│   │   │   ├── orders.py         # Order placement + history + detail
│   │   │   ├── insights.py       # Recently viewed + continue shopping
│   │   │   └── admin.py          # Train, stats, right to forget
│   ├── data/                     # Model checkpoints + SQLite DB
│   ├── scripts/
│   │   ├── start_backend.ps1     # Canonical backend start (kills stale, starts, waits for health)
│   │   └── stop_backend.ps1      # Cleanly stop all backend processes + free the port
│   ├── pyproject.toml            # ruff lint configuration
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
│   │       ├── PrivacyModal.tsx   # Privacy policy + consent modal
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

### Verified against the real dataset

Measured locally (same architecture as deployed: in-memory TruncatedSVD via
scikit-learn, single-process uvicorn, single-writer SQLite with WAL) on the
full real database — not just a handful of synthetic customers:

| Metric | Measured value |
|---|---|
| Dataset verified | **560 customers** (266 with behavioural events), **760 products**, **5,777 events**, 269 consenting |
| Model training (full retrain) | **~0.3 s** total (feature build ~0.11 s, SVD fit ~0.016 s, 50 components, 266×760 matrix, 1.06 MB `model.pkl`) |
| Batch recommendation refresh (`/api/admin/train` store phase, 269 customers) | **~36 s** total — scoring ~17 s, SQLite delete+insert persist ~19 s |
| Live recommendation GET (cold, sequential) | **p50 ~19 ms, p95 ~53 ms** |
| Concurrent burst (43 simultaneous GETs, distinct customers) | **no errors, ~37 req/s, p50 ~735 ms, p95 ~1.1 s** |
| `/api/admin/train` during 50 concurrent GETs | **no errors/timeouts**; training runs in background (~36 s) and reads degraded to **p50 ~1.9 s, p95 ~3.2 s**; engine swaps atomically on completion |
| Offer assignment (`assign_offers`) | **~0.03 s** for 269 customers / 135 assignments |
| Model RAM footprint | ~3 MB total (user factors 266×50, item factors 760×50, content vectors 760×131) |

Correctness at this scale:

- **266/266 event-having customers served personalised `svd` recs** (261 distinct
  lists; at most 3 customers shared an identical list). No trace of the old
  pre-fix symptom where everyone got one generic popular list.
- **98.5%** of event-having customers have their dominant browsing category
  inside the top-10 recs; **78.9%** have it as the #1 recommendation. The 4/266
  exceptions are expected collaborative-filtering behaviour (customer bought
  most of what they browsed, so remaining recs come from similar neighbours) —
  not a correctness bug.
- Customers with **no behavioural events** (294) correctly get the global
  popularity list as the last resort; consenting signup-preference customers are
  served `cold_start` instead.
- Only customers with active consent (269) are written to
  `recommendations`.

### Honest ceiling (measured, not guessed)

- The **recommendation model is not the bottleneck** at this scale: training is
  ~0.3 s and the SVD factors fit in ~3 MB of RAM. Even at the 500K-customer /
  20K-SKU design target, model RAM stays well under 200 MB and SVD refit is
  estimated in seconds-to-minutes (not verified at that size).
- The first real ceiling is the **batch refresh**: it costs **~0.13 s per
  customer** (per-customer delete + insert + reason-code pass on single-writer
  SQLite). Expected to scale roughly linearly → ~5 min at 5K customers, ~55 min
  at 50K, several hours at 500K. A bulk-upsert + batched reason-coding would be
  the lever here, not a rewrite.
- The second ceiling is **concurrent live reads**: a single-instance SQLite
  backend sustains **~30-40 reads/s with sub-second p95** up to ~50 simultaneous
  requests. Beyond ~50 concurrent the p95 crosses 1 s, and a concurrent
  `/admin/train` write burst pushes read p95 to ~3 s (still no errors at this
  dataset size). Beyond ~a few hundred concurrent users, SQLite
  single-writer contention and the per-recommendation product-enrichment queries
  are what degrade first.
- Caching: the recs cache requires **Redis** and silently no-ops without it, so
  every local/demo GET hits the DB. A Redis-backed cache (or any in-process
  cache) would materially lift the concurrent-read ceiling — the integration
  point is already wired in `app/cache.py`.

Design target (NOT a claim that this build already operates there):

- **500K customers**, **20K SKUs**, **2M events/day**
- **Storage**: PostgreSQL handles this comfortably with proper indexing (composite indexes on `(customer_id, event_type)` and `event_timestamp DESC`)
- **Training**: TruncatedSVD with 50 components trains in minutes at this scale
- **Recommendation serving**: Near-real-time via precomputed recommendations or live model inference. The live-inference path only ever scans that customer's own events (not the full event table)
- **Batch cycle**: Daily segment refresh + offer assignment is O(n) in customer count — in production this moves to a scheduled async job rather than the synchronous demo path
- **Caching**: Redis caches popular recommendations to reduce DB load
- **Rate limiting**: in-memory in the demo; production uses the Redis-backed limiter (integration point is wired)
- **Currency conversion**: Server-side with configurable rates, extendable to live forex APIs
