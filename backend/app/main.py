"""
FastAPI application entry point for the Retail Hyper-Personalisation Engine.
Initialises database, seeds data, loads ML model, and registers all routers.
Serves production frontend build from frontend/dist when available.
"""
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException

from app.config import settings
from app.database import create_tables, engine, async_session_factory
from app.models import Event, Customer
from app.seed_data import seed_database, ensure_demo_passwords
from app.offers import OfferEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Global recommender engine instance ──
recommender_engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown tasks."""
    global recommender_engine

    # ── Startup ──
    logger.info("Starting Retail Hyper-Personalisation Engine...")

    # Ensure data directory exists (for SQLite)
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)

    # Create tables
    await create_tables()
    logger.info("Database tables created/verified.")

    # Seed data if empty
    async with async_session_factory() as db:
        await seed_database(db)
        # Backfill demo passwords for any legacy/seed accounts lacking one.
        await ensure_demo_passwords(db)
        # Always seed offers & assign them (runs even if DB already seeded)
        offer_engine = OfferEngine(db)
        await offer_engine.seed_offers()
        await offer_engine.assign_offers()
        await db.commit()

    # Load recommender model
    from app.recommender import RecommendationEngine
    recommender_engine = RecommendationEngine(settings)
    loaded = recommender_engine.load()
    if loaded:
        logger.info("Recommender model loaded from disk.")
    else:
        logger.info("No pre-trained model found. Use POST /api/admin/train to train one.")

    # Set global engine references in routers
    from app.routers import recommendations as rec_router
    from app.routers import admin as admin_router
    rec_router.set_recommender_engine(recommender_engine)
    admin_router.set_recommender_engine(recommender_engine)

    logger.info("Application startup complete.")
    yield

    # ── Shutdown ──
    logger.info("Shutting down...")
    from app.cache import close_redis
    await close_redis()
    await engine.dispose()
    logger.info("Engine disposed.")


# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Import and register routers ──────────────────────────────────────────────

from app.routers import events, customers, recommendations, offers, admin, products as products_router

app.include_router(events.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(offers.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(products_router.router, prefix="/api")

from app.routers import orders as orders_router
app.include_router(orders_router.router, prefix="/api")

# Auth
from app.routers import auth as auth_router
app.include_router(auth_router.router, prefix="/api")

# Customer insights
from app.routers import insights as insights_router
app.include_router(insights_router.router, prefix="/api")

# MCP OAuth
from app.mcp import router as mcp_router
app.include_router(mcp_router.router)


# ── Health Check ─────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "title": settings.APP_TITLE,
        "version": settings.APP_VERSION,
    }


# ── Serve production frontend build ──────────────────────────────────────────

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        if request.url.path.startswith("/api"):
            from fastapi.responses import JSONResponse
            if isinstance(exc, HTTPException):
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        index_path = FRONTEND_DIST / "index.html"
        if index_path.is_file():
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=index_path.read_text(), status_code=200)
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    logger.info("Serving frontend from %s", FRONTEND_DIST)
else:
    logger.info("No frontend build found at %s — API-only mode.", FRONTEND_DIST)


# ── Direct run ───────────────────────────────────────────────────────────────
# Note: reload is OFF by default. `--reload` spawns a reloader + worker pair and
# on Windows the venv launcher adds another child, which historically produced
# confusing duplicate processes and port conflicts. Use scripts/start_backend.ps1
# for the canonical single-process start.

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=os.environ.get("RELOAD", "0").strip().lower() in ("1", "true", "yes"),
    )
