"""
FastAPI application entry point for the Retail Hyper-Personalisation Engine.
Initialises database, seeds data, loads ML model, and registers all routers.
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func

from app.config import settings
from app.database import create_tables, engine, async_session_factory
from app.models import Event, Customer
from app.seed_data import seed_database

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

    # Create tables
    await create_tables()
    logger.info("Database tables created/verified.")

    # Seed data if empty
    async with async_session_factory() as db:
        await seed_database(db)
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


# ── Direct run ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
