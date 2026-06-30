# Retail Hyper-Personalisation Engine

A production-grade retail personalisation system that generates individualised offers and product recommendations based on customer behaviour data. Built with privacy by design — consent-gated, GDPR/DPDP Act compliant, with no sensitive-attribute inference.

## Architecture

```
┌──────────────────────┐      ┌──────────────────┐
│   React Frontend     │──────▶  FastAPI Backend │
│   (Vite + TS + TW)   │◀──────│  (Python 3.12)  │
└──────────────────────┘      └────────┬─────────┘
                                       │
                  ┌────────────────────┼────────────────────┐
                  ▼                    ▼                    ▼
          ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
          │   Postgres   │    │    Redis      │    │  Model File  │
          │  (Events,    │    │  (Cache)      │    │  (joblib)    │
          │   Customers, │    └──────────────┘    └──────────────┘
          │   Products)  │
          └──────────────┘
```

### Components

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS | Dashboard UI — search customers, view personalised recs with reason codes, see active offers |
| **API** | FastAPI (async) | REST endpoints for events, customers, recommendations, offers, admin |
| **Database** | PostgreSQL 16 (async via asyncpg) | Behavioural events, customer profiles, products, segments, offers |
| **Cache** | Redis | Session cache, rate limiting |
| **ML Engine** | scikit-learn TruncatedSVD + cosine similarity | Hybrid collaborative + content-based filtering |

## Features

### 1. Hyper-Personalised Recommendations
- **Hybrid scoring**: 70% collaborative filtering + 30% content-based similarity
- **Weighted interactions**: Purchases (5x), cart adds (3x), wishlist (2.5x), email clicks (2x), page views (1x)
- **Interpretable reason codes**: Every recommendation includes a human-readable reason:
  - `purchased_category` — "You previously purchased Electronics items"
  - `viewed_category` — "You've been browsing Clothing"
  - `viewed_product` — "You viewed this item recently"
  - `cart_recovery` — "This item was in your cart"
  - `wishlist_item` — "This item is on your wishlist"
  - `trending_in_segment` — "Popular among similar customers"
  - `top_pick` — "Recommended based on your browsing patterns"

### 2. Segment-Based Offer Engine
- 8 behavioural segments with hardcoded business rules:
  - `high_value`, `bargain_hunter`, `new_user`, `lapsed`, `cart_abandoner`, `brand_loyalist`, `window_shopper`, `power_user`
- 8 predefined offers targeted to these segments
- Daily batch segment refresh + offer assignment

### 3. Privacy Guardrails
- **Consent-gated**: All personalisation requires explicit consent
- **GDPR/DPDP right to forget**: Deletes all behavioural data while keeping minimal record
- **No sensitive attributes**: All features are behavioural only — no age, gender, location, or demographics
- **Audit trail**: Full consent_log with action, regulator (GDPR/DPDP), and timestamp
- **Transparent reason codes**: Every recommendation explains why it was made — no black boxes

## Quick Start

### With Docker Compose (recommended)

```bash
docker compose up --build
```

This starts:
- Postgres on `:5432`
- Redis on `:6379`
- Backend API on `http://localhost:8000`
- Frontend on `http://localhost:5173`

The backend automatically:
1. Creates database tables
2. Seeds 500 customers, 100 products, and ~10,000 behavioural events
3. Loads a pre-trained model if available

### Without Docker

**Backend:**
```bash
cd backend
pip install -r requirements.txt
# Start Postgres and Redis separately, then:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/events` | Ingest behaviour event |
| `GET` | `/api/customers/search?q=` | Search customers by name/email |
| `GET` | `/api/customers/{id}` | Customer profile with metrics + segments |
| `GET` | `/api/customers/{id}/recommendations` | Top 10 personalised recs (consent-gated) |
| `GET` | `/api/customers/{id}/offers` | Active offers for customer |
| `POST` | `/api/admin/train` | Trigger model training (background) |
| `POST` | `/api/admin/right-to-forget/{id}` | GDPR/DPDP right to forget |

## Training the Model

Visit the frontend dashboard and click **"Train Model"** or call the API directly:

```bash
curl -X POST http://localhost:8000/api/admin/train
```

Training runs in the background. Once complete, recommendations become available for all consenting customers.

## Privacy & Compliance

### Consent Flow
1. Customer record has `consent_given` boolean (set during seeding)
2. All personalisation endpoints check consent before returning data
3. If consent is revoked, 403 is returned immediately
4. Consent actions are logged in `consent_log` with regulator tracking

### Right to Forget
```bash
curl -X POST http://localhost:8000/api/admin/right-to-forget/{customer_id}
```
This:
- Deletes all behavioural events for the customer
- Removes recommendations, segments, and offers
- Revokes consent
- Logs the action (minimal record is kept)

### What We DON'T Do
- No demographic profiling (age, gender, location)
- No sensitive attribute inference
- No third-party data enrichment
- No dark patterns or deceptive personalisation

## Project Structure

```
retail-personalisation/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point + lifespan
│   │   ├── config.py             # Settings via env vars
│   │   ├── database.py           # Async SQLAlchemy engine
│   │   ├── models.py             # ORM models (8 tables)
│   │   ├── schemas.py            # Pydantic v2 schemas
│   │   ├── recommender.py        # Hybrid CF + CBF engine (SVD)
│   │   ├── offers.py             # Segment logic + offer assignment
│   │   ├── privacy.py            # Consent service + right to forget
│   │   ├── seed_data.py          # Synthetic data generator
│   │   └── routers/
│   │       ├── events.py         # Event ingestion
│   │       ├── customers.py      # Customer search + profile
│   │       ├── recommendations.py# Personalised recs
│   │       ├── offers.py         # Customer offers
│   │       └── admin.py          # Train + right to forget
│   ├── data/                     # Model checkpoints
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Main dashboard layout
│   │   ├── api/client.ts         # API client
│   │   ├── types.ts              # TypeScript interfaces
│   │   └── components/
│   │       ├── CustomerSearch.tsx  # Search + select customer
│   │       ├── CustomerProfile.tsx # Profile card + metrics grid
│   │       ├── RecommendationsPanel.tsx # Recs grid + reason badges
│   │       ├── OffersPanel.tsx      # Active offers list
│   │       └── ReasonCodeBadge.tsx  # Color-coded reason tags
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Scale Readiness

The system is designed for the specified scale:
- **500K customers**, **20K SKUs**, **2M events/day**
- **Storage**: PostgreSQL handles this comfortably with proper indexing (we use composite indexes on `(customer_id, event_type)` and `event_timestamp DESC`)
- **Training**: TruncatedSVD with 50 components trains in minutes at this scale
- **Recommendation serving**: Near-real-time (minutes) via precomputed recommendations or live model inference
- **Batch cycle**: Daily segment refresh + offer assignment is O(n) in customer count
- **Caching**: Redis caches popular recommendations to reduce DB load
