"""Admin endpoints.

POST /api/admin/train --- trigger model training
POST /api/admin/right-to-forget/{customer_id} --- GDPR right to forget
"""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

import pandas as pd

from app.database import get_db, async_session_factory
from app.models import Customer, Event, Product, Recommendation
from app.offers import OfferEngine
from app.schemas import TrainOut, AdminActionOut, AssignOffersOut, SystemStatsOut, SegmentCountOut
from app.privacy import ConsentService
from app.config import settings
from app.utils import utcnow
from app.cache import cache_delete

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])

# Global reference to the recommender engine
recommender_engine = None


from app.security import get_current_customer


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

    asyncio.create_task(run_training())
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
        select(func.count(Customer.customer_id)).where(Customer.consent_given == True)
    )
    consent_count = consent_result.scalar() or 0
    consent_rate = round(consent_count / total_customers * 100, 1) if total_customers > 0 else 0.0

    events_result = await db.execute(select(func.count(Event.event_id)))
    total_events = events_result.scalar() or 0

    products_result = await db.execute(select(func.count(Product.product_id)))
    total_products = products_result.scalar() or 0

    from app.models import Offer, CustomerOffer, CustomerSegment

    offers_result = await db.execute(select(func.count(Offer.offer_id)))
    total_offers = offers_result.scalar() or 0

    # Active offers (based on valid_until)
    now = utcnow()
    active_result = await db.execute(
        select(func.count(Offer.offer_id)).where(
            Offer.is_active == True,
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
    """Background task: fetch data and train the model.

    The expensive parts (SVD fit, content-feature building, per-customer
    scoring) run via asyncio.to_thread so they NEVER block the event loop —
    the API stays responsive to other requests while the model retrains.
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

            # Heavy CPU-bound model training, off the event loop.
            await asyncio.to_thread(recommender_engine.train, events_df, products_df)

            # Store recommendations (scoring threaded, DB writes async)
            await _store_recommendations(db)

            await db.commit()
            logger.info("Model training completed successfully.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Training failed: {e}", exc_info=True)


async def _store_recommendations(db) -> None:
    """Generate and persist recommendations for all consenting customers.

    All per-customer scoring (SVD inference + reason-code lookups) runs in a
    worker thread via asyncio.to_thread so a large customer base can't stall
    the API; only the DB deletes/inserts happen here (async).
    """
    from sqlalchemy import delete

    # Get all customers with consent
    result = await db.execute(
        select(Customer).where(Customer.consent_given == True)
    )
    customers = result.scalars().all()

    if not customers:
        logger.warning("No consenting customers found for recommendations.")
        return

    now = utcnow()

    # Pre-fetch everything the scoring thread needs (async, non-blocking).
    products_result = await db.execute(select(Product))
    all_products = products_result.scalars().all()
    products_df = pd.DataFrame([
        {"product_id": p.product_id, "category": p.category}
        for p in all_products
    ])

    events_result = await db.execute(select(Event))
    all_events = events_result.scalars().all()
    events_data = [
        {
            "customer_id": e.customer_id,
            "product_id": e.product_id,
            "event_type": e.event_type,
        }
        for e in all_events
    ]
    events_df = pd.DataFrame(events_data) if events_data else pd.DataFrame()

    def _compute_all() -> dict:
        """Score + explain every consenting customer (CPU-bound, off-loop)."""
        computed = {}
        for customer in customers:
            try:
                # Get recommendations (the engine handles filtering internally)
                recs = recommender_engine.recommend(
                    customer_id=customer.customer_id,
                    n=10,
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
                if not events_df.empty and not products_df.empty:
                    customer_events = events_df[
                        events_df["customer_id"] == customer.customer_id
                    ]
                    for rec in recs:
                        try:
                            rc, rt = recommender_engine.get_reason_code(
                                customer.customer_id,
                                rec["product_id"],
                                customer_events,
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
