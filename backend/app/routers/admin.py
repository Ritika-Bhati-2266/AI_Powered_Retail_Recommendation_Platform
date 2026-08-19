"""Admin endpoints.

POST /api/admin/train --- trigger model training
POST /api/admin/right-to-forget/{customer_id} --- GDPR right to forget
"""
import asyncio
import logging

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_delete
from app.config import settings
from app.database import async_session_factory, get_db
from app.models import Customer, Event, Product, Recommendation
from app.offers import OfferEngine
from app.privacy import ConsentService
from app.recommender import RecommendationEngine
from app.schemas import AdminActionOut, AssignOffersOut, SegmentCountOut, SystemStatsOut, TrainOut
from app.security import get_current_customer
from app.utils import utcnow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])

# Global reference to the recommender engine
recommender_engine = None

# Strong references to in-flight background tasks so they aren't GC'd.
_background_tasks: set = set()


def set_recommender_engine(engine):
    """Inject recommender engine from main.py."""
    global recommender_engine
    recommender_engine = engine


async def verify_admin_access(
    customer: Customer = Depends(get_current_customer),
) -> Customer:
    """Require a valid bearer token whose account role is 'admin'.

    Admin privilege is determined from the token-authenticated customer's role
    in the database — not from a trustable-on-its-own email header.
    """
    if customer.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied. Admin privileges required."
        )
    return customer


@router.post("/admin/train", response_model=TrainOut)
async def trigger_training(
    db: AsyncSession = Depends(get_db),
    admin: Customer = Depends(verify_admin_access),
):
    """Trigger model training in the background."""
    if recommender_engine is None:
        raise HTTPException(status_code=503, detail="Recommender engine not available")

    _background_tasks.add(asyncio.create_task(run_training()))
    return TrainOut()


@router.post("/admin/assign-offers", response_model=AssignOffersOut)
async def trigger_offer_assignment(
    db: AsyncSession = Depends(get_db),
    admin: Customer = Depends(verify_admin_access),
):
    """Re-run offer assignment: clears old assignments and assigns
    offers to all customers based on their current segments."""
    offer_engine = OfferEngine(db)
    count = await offer_engine.assign_offers()
    await db.commit()
    logger.info(f"Offer assignment completed: {count} assignments.")
    return AssignOffersOut(assignments_count=count)


@router.get("/admin/stats", response_model=SystemStatsOut)
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    admin: Customer = Depends(verify_admin_access),
):
    """Get system-wide statistics including segment distribution."""
    # Total counts
    customers_result = await db.execute(select(func.count(Customer.customer_id)))
    total_customers = customers_result.scalar() or 0

    consent_result = await db.execute(
        select(func.count(Customer.customer_id)).where(Customer.consent_given)
    )
    consent_count = consent_result.scalar() or 0
    consent_rate = round(consent_count / total_customers * 100, 1) if total_customers > 0 else 0.0

    events_result = await db.execute(select(func.count(Event.event_id)))
    total_events = events_result.scalar() or 0

    products_result = await db.execute(select(func.count(Product.product_id)))
    total_products = products_result.scalar() or 0

    from app.models import CustomerOffer, CustomerSegment, Offer

    offers_result = await db.execute(select(func.count(Offer.offer_id)))
    total_offers = offers_result.scalar() or 0

    # Active offers (based on valid_until)
    now = utcnow()
    active_result = await db.execute(
        select(func.count(Offer.offer_id)).where(
            Offer.is_active,
            Offer.valid_from <= now,
            Offer.valid_until >= now,
        )
    )
    active_offers = active_result.scalar() or 0

    assignments_result = await db.execute(select(func.count(CustomerOffer.customer_id)))
    total_assignments = assignments_result.scalar() or 0

    # Segment distribution
    segment_result = await db.execute(
        select(
            CustomerSegment.segment,
            func.count(CustomerSegment.customer_id).label("cnt"),
        )
        .group_by(CustomerSegment.segment)
        .order_by(func.count(CustomerSegment.customer_id).desc())
    )
    segment_rows = segment_result.fetchall()
    segment_distribution = [
        SegmentCountOut(segment=row[0], count=row[1])
        for row in segment_rows
    ]

    logger.info(f"System stats: {total_customers} customers, {consent_rate}% consent rate")
    return SystemStatsOut(
        total_customers=total_customers,
        consent_rate=consent_rate,
        total_events=total_events,
        total_products=total_products,
        total_offers=total_offers,
        active_offers=active_offers,
        total_assignments=total_assignments,
        segment_distribution=segment_distribution,
    )


async def run_training() -> None:
    """Background task: fetch data, train a fresh model, and atomically swap it
    into service.

    The expensive parts (SVD fit, content-feature building, per-customer
    scoring) run via asyncio.to_thread so they NEVER block the event loop —
    the API stays responsive to other requests while the model retrains.

    A brand-new engine instance is trained rather than mutating the live one in
    place: that way a request that arrives mid-training never observes a
    half-rebuilt matrix/index. Only once training AND stored-recommendation
    refresh have both succeeded is the new engine swapped into the routers, and
    it is persisted to disk (train() -> save()) so a process restart loads the
    same fresh snapshot.
    """
    async with async_session_factory() as db:
        try:
            logger.info("Starting model training...")

            # Fetch all events
            result = await db.execute(select(Event))
            events = result.scalars().all()

            if not events:
                logger.warning("No events found for training.")
                return

            # Convert to pandas
            events_data = [
                {
                    "event_id": e.event_id,
                    "customer_id": e.customer_id,
                    "product_id": e.product_id,
                    "event_type": e.event_type,
                    "event_timestamp": e.event_timestamp,
                }
                for e in events
            ]
            events_df = pd.DataFrame(events_data)

            # Fetch all products
            result = await db.execute(select(Product))
            products = result.scalars().all()
            products_data = [
                {
                    "product_id": p.product_id,
                    "name": p.name,
                    "category": p.category,
                    "subcategory": p.subcategory,
                    "brand": p.brand,
                    "price": p.price,
                    "image_url": p.image_url,
                    "rating": p.rating,
                    "discount_percent": p.discount_percent,
                    "original_price": p.original_price,
                }
                for p in products
            ]
            products_df = pd.DataFrame(products_data)

            # Ensure string types (cheap, stays on the loop)
            for col in ["customer_id", "product_id", "event_type"]:
                if col in events_df.columns:
                    events_df[col] = events_df[col].astype(str)

            for col in ["product_id", "category", "brand"]:
                if col in products_df.columns:
                    products_df[col] = products_df[col].astype(str)

            # Train into a fresh engine (never mutates the live one mid-read).
            new_engine = RecommendationEngine(settings)
            await asyncio.to_thread(new_engine.train, events_df, products_df)
            if not new_engine._is_trained:
                logger.warning("Training produced no usable model — keeping the current engine.")
                return

            # Store recommendations using the freshly trained engine.
            await _store_recommendations(db, new_engine, events_df, products_df)

            await db.commit()

            # Atomically swap the live engine with the trained snapshot so all
            # subsequent inference uses exactly what was just trained.
            _swap_engine(new_engine)

            logger.info("Model training completed successfully.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Training failed: {e}", exc_info=True)


def _swap_engine(engine) -> None:
    """Replace the in-memory engine shared by the recommendation/admin routers."""
    global recommender_engine
    recommender_engine = engine
    from app.routers import recommendations as recommendations_router

    set_recommender_engine(engine)
    recommendations_router.set_recommender_engine(engine)
    logger.info("Live recommender engine swapped to freshly trained snapshot.")


async def _store_recommendations(
    db, engine, events_df: pd.DataFrame | None = None, products_df: pd.DataFrame | None = None
) -> None:
    """Generate and persist recommendations for all consenting customers.

    All per-customer scoring (SVD inference + reason-code lookups) runs in a
    worker thread via asyncio.to_thread so a large customer base can't stall
    the API; only the DB deletes/inserts happen here (async).

    The engine's live event data is passed through so customers absent from the
    trained user matrix (new signups) are still served personalised recs via
    the SVD live-projection path instead of the global popular list.
    """
    from sqlalchemy import delete

    # Get all customers with consent
    result = await db.execute(
        select(Customer).where(Customer.consent_given)
    )
    customers = result.scalars().all()

    if not customers:
        logger.warning("No consenting customers found for recommendations.")
        return

    now = utcnow()

    # Pre-fetch everything the scoring thread needs (async, non-blocking).
    if products_df is None or len(products_df) == 0:
        products_result = await db.execute(select(Product))
        all_products = products_result.scalars().all()
        products_df = pd.DataFrame([
            {"product_id": p.product_id, "category": p.category}
            for p in all_products
        ])
    else:
        products_df = products_df[["product_id", "category"]].copy()

    if events_df is None or len(events_df) == 0:
        events_result = await db.execute(select(Event))
        all_events = events_result.scalars().all()
        events_df = pd.DataFrame([
            {
                "customer_id": e.customer_id,
                "product_id": e.product_id,
                "event_type": e.event_type,
            }
            for e in all_events
        ])
    else:
        events_df = events_df[["customer_id", "product_id", "event_type"]].copy()

    def _compute_all() -> dict:
        """Score + explain every consenting customer (CPU-bound, off-loop)."""
        computed = {}
        for customer in customers:
            try:
                # Get recommendations (the engine handles filtering internally).
                # Passing the customer's own events enables SVD projection +
                # behavior-aware cold start for customers not in the matrix.
                recs = engine.recommend(
                    customer_id=customer.customer_id,
                    n=10,
                    events_df=events_df,
                    products_df=products_df,
                )

                if not recs:
                    continue

                # Deduplicate by product_id, keeping the highest-scored entry
                seen = {}
                for rec in recs:
                    pid = rec["product_id"]
                    if pid not in seen or rec["score"] > seen[pid]["score"]:
                        seen[pid] = rec
                recs = sorted(seen.values(), key=lambda r: r["score"], reverse=True)

                # Rich, interpretable reason codes from the customer's own events
                for rec in recs:
                    try:
                        rc, rt = engine.get_reason_code(
                            customer.customer_id,
                            rec["product_id"],
                            events_df,
                            products_df,
                        )
                        rec["reason_code"] = rc
                        rec["reason_text"] = rt
                    except Exception:
                        pass

                computed[customer.customer_id] = recs
            except Exception as e:
                logger.warning(f"Failed to generate recommendations for {customer.customer_id}: {e}")
                continue
        return computed

    computed = await asyncio.to_thread(_compute_all)

    stored_count = 0
    for customer_id, recs in computed.items():
        # Delete existing recommendations before inserting fresh ones
        await db.execute(
            delete(Recommendation).where(
                Recommendation.customer_id == customer_id
            )
        )
        for rec in recs:
            recommendation = Recommendation(
                customer_id=customer_id,
                product_id=rec["product_id"],
                score=rec["score"],
                reason_code=rec.get("reason_code") or "top_pick",
                reason_text=rec.get("reason_text") or "Recommended for you",
                generated_at=now,
            )
            db.add(recommendation)
        stored_count += 1

    await db.flush()
    # Invalidate recommendation cache for all customers
    try:
        await cache_delete("recs:*")
    except Exception:
        pass
    logger.info(f"Stored recommendations for {stored_count} customers.")


@router.post("/admin/right-to-forget/{customer_id}", response_model=AdminActionOut)
async def right_to_forget(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    admin: Customer = Depends(verify_admin_access),
):
    """GDPR/DPDP Right to Forget — delete all customer data."""
    # Check customer exists
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    consent_service = ConsentService(db)
    await consent_service.right_to_forget(customer_id)
    await db.commit()

    logger.info(f"Right to forget executed for customer {customer_id}")
    return AdminActionOut(status="forgotten")
