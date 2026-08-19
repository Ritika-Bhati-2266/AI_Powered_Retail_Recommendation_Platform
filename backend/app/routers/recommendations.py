"""Recommendations endpoint.
GET /api/customers/{customer_id}/recommendations
"""
import json
import logging
from datetime import timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_get, cache_set
from app.currency import convert_price
from app.database import get_db
from app.models import (
    Customer,
    CustomerCategoryPreference,
    Event,
    Product,
    Recommendation,
)
from app.privacy import ConsentService
from app.schemas import RecommendationOut
from app.security import require_owner
from app.serializers import convert_original_price
from app.utils import utcnow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["recommendations"])

# Global reference to the recommender engine (set in main.py on startup)
recommender_engine = None


def set_recommender_engine(engine):
    """Allow main.py to inject the recommender engine instance."""
    global recommender_engine
    recommender_engine = engine


def _deduplicate_recommendations(recs: list) -> list:
    """Deduplicate by product_id, keeping the highest-scored entry."""
    seen = {}
    for rec in recs:
        pid = rec.product_id
        if pid not in seen or rec.score > seen[pid].score:
            seen[pid] = rec
    return sorted(seen.values(), key=lambda r: r.score, reverse=True)


def _convert_rec_price(rec: dict, currency: str) -> dict:
    """Apply currency conversion to a recommendation dict and return it with currency+symbol."""
    converted_price, cur, sym = convert_price(rec.get("price", 0), currency)
    rec["price"] = converted_price
    rec["currency"] = cur
    rec["symbol"] = sym
    if "original_price" in rec:
        rec["original_price"] = convert_original_price(rec.get("original_price"), currency)
    return rec


@router.get("/customers/{customer_id}/recommendations", response_model=list[RecommendationOut])
async def get_recommendations(
    customer_id: str,
    auth: Customer = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get top 10 personalised recommendations for a customer."""
    # 1. Check consent BEFORE the cache: a revoked consent must never receive
    #    cached personalisation from Redis.
    consent_service = ConsentService(db)
    has_consent = await consent_service.check_consent(customer_id)
    if not has_consent:
        raise HTTPException(
            status_code=403,
            detail="Customer has not given consent for personalisation. Recommendations are unavailable.",
        )

    # 2. Check customer exists and get currency
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer_currency = customer.currency or "USD"

    # 3. Try cache first
    cache_key = f"recs:{customer_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        try:
            data = json.loads(cached)
            return [RecommendationOut(**item) for item in data]
        except Exception:
            pass

    # 4. Check event count for this customer (used to decide cold-start vs model)
    event_count_result = await db.execute(
        select(func.count(Event.event_id))
        .where(Event.customer_id == customer_id)
    )
    customer_event_count = event_count_result.scalar() or 0

    # 5. Cold-start: use signup category preferences for new customers with no events
    if customer_event_count == 0:
        cat_pref_result = await db.execute(
            select(CustomerCategoryPreference.category)
            .where(CustomerCategoryPreference.customer_id == customer_id)
        )
        preferred_categories = cat_pref_result.scalars().all()
        if preferred_categories:
            cold_start_products = await db.execute(
                select(Product)
                .where(Product.category.in_(preferred_categories))
                .order_by(Product.name)
                .limit(10)
            )
            cold_products = cold_start_products.scalars().all()
            if cold_products:
                result = []
                for idx, p in enumerate(cold_products):
                    converted_price, cur, sym = convert_price(p.price, customer_currency)
                    result.append(RecommendationOut(
                        product_id=p.product_id,
                        name=p.name,
                        category=p.category or "",
                        subcategory=p.subcategory,
                        brand=p.brand,
                        price=converted_price,
                        currency=cur,
                        symbol=sym,
                        image_url=p.image_url,
                        rating=p.rating,
                        discount_percent=p.discount_percent,
                        original_price=convert_original_price(p.original_price, customer_currency),
                        score=1.0 / (idx + 1),
                        reason_code="cold_start",
                        reason_text=f"Based on your interest in {p.category}",
                        source="cold_start",
                    ))
                if result:
                    logger.info("Customer %s: served signup-preference cold start (%d prefs).", customer_id, len(preferred_categories))
                    return _deduplicate_recommendations(result)

    # 6. Try model-based recommendations (only for customers with events)
    if customer_event_count > 0 and recommender_engine and recommender_engine._is_trained:
        # Check if we have stored recommendations
        stored = await db.execute(
            select(Recommendation)
            .where(Recommendation.customer_id == customer_id)
            .order_by(Recommendation.score.desc())
            .limit(10)
        )
        stored_recs = stored.scalars().all()

        if stored_recs:
            # Enrich with product details
            recommendations = []
            for rec in stored_recs:
                prod_result = await db.execute(
                    select(Product).where(Product.product_id == rec.product_id)
                )
                product = prod_result.scalar_one_or_none()
                if product:
                    base_price = product.price
                    converted_price, cur, sym = convert_price(base_price, customer_currency)
                    recommendations.append(RecommendationOut(
                        product_id=product.product_id,
                        name=product.name,
                        category=product.category or "",
                        subcategory=product.subcategory,
                        brand=product.brand,
                        price=converted_price,
                        currency=cur,
                        symbol=sym,
                        image_url=product.image_url,
                        rating=product.rating,
                        discount_percent=product.discount_percent,
                        original_price=convert_original_price(product.original_price, customer_currency),
                        score=rec.score,
                        reason_code=rec.reason_code or "top_pick",
                        reason_text=rec.reason_text or "Recommended for you",
                        source="svd",
                    ))
            if recommendations:
                deduped = _deduplicate_recommendations(recommendations)
                try:
                    await cache_set(cache_key, json.dumps([r.model_dump() for r in deduped], default=str), ttl=300)
                except Exception:
                    pass
                logger.info("Customer %s: served %d stored personalised recommendations.", customer_id, len(deduped))
                return deduped

        # Fallback: use the in-memory model to generate live recommendations.
        # Collaborative scores come from the precomputed factor matrices, so the
        # per-request event load only needs THIS customer's history (for the
        # purchased-exclusion set and reason-code lookups). Loading the whole
        # Event table per request would be O(all events) and collapse at
        # production scale — stored recommendations from /api/admin/train are
        # the preferred serving path.
        try:
            # Build events and products DataFrames for the recommender
            events_result = await db.execute(
                select(Event).where(Event.customer_id == customer_id)
            )
            all_events = events_result.scalars().all()
            events_list = [
                {
                    "event_id": e.event_id,
                    "customer_id": e.customer_id,
                    "product_id": e.product_id,
                    "event_type": e.event_type,
                    "event_timestamp": e.event_timestamp,
                }
                for e in all_events
            ]
            events_df = pd.DataFrame(events_list) if events_list else pd.DataFrame()

            products_result = await db.execute(select(Product))
            all_products = products_result.scalars().all()
            products_list = [
                {
                    "product_id": p.product_id,
                    "name": p.name,
                    "category": p.category,
                    "subcategory": p.subcategory,
                    "brand": p.brand,
                    "price": p.price,
                    "image_url": p.image_url,
                }
                for p in all_products
            ]
            products_df = pd.DataFrame(products_list) if products_list else pd.DataFrame()

            model_recs = recommender_engine.recommend(
                customer_id=customer_id,
                n=10,
                events_df=events_df,
                products_df=products_df,
            )

            if model_recs:
                live_recs = [
                    RecommendationOut(**{
                        **_convert_rec_price(r, customer_currency),
                        "subcategory": r.get("subcategory", ""),
                        "brand": r.get("brand", ""),
                        "image_url": r.get("image_url", ""),
                    })
                    for r in model_recs
                ]
                sources = {getattr(r, "source", "svd") for r in live_recs}
                logger.info(
                    "Customer %s: served %d live model recommendations (source=%s).",
                    customer_id, len(live_recs), sorted(sources) or ["svd"],
                )
                return _deduplicate_recommendations(live_recs)
            logger.info("Customer %s: model produced no recommendations; trying behavior-aware cold start.", customer_id)
        except Exception as e:
            logger.warning(f"Live recommendation failed for customer {customer_id}: {e}")

    # 6.5 Behavior-aware cold start: the customer has events but no usable model
    #     signal (model untrained/absent). Bias toward the categories the
    #     customer actually browses, instead of a generic global "popular" list.
    if customer_event_count > 0:
        cold_categories = await _recent_category_interests(customer_id, db)
        if cold_categories:
            cold_start_products = await db.execute(
                select(Product)
                .where(Product.category.in_(cold_categories))
                .order_by(Product.name)
                .limit(20)
            )
            all_cold = cold_start_products.scalars().all()
            if all_cold:
                # Prefer products from the customer's top category first.
                top_cat = cold_categories[0]
                ranked = sorted(
                    all_cold,
                    key=lambda p: (0 if p.category == top_cat else 1, p.name),
                )[:10]
                result = []
                for idx, p in enumerate(ranked):
                    converted_price, cur, sym = convert_price(p.price, customer_currency)
                    result.append(RecommendationOut(
                        product_id=p.product_id,
                        name=p.name,
                        category=p.category or "",
                        subcategory=p.subcategory,
                        brand=p.brand,
                        price=converted_price,
                        currency=cur,
                        symbol=sym,
                        image_url=p.image_url,
                        rating=p.rating,
                        discount_percent=p.discount_percent,
                        original_price=convert_original_price(p.original_price, customer_currency),
                        score=1.0 / (idx + 1),
                        reason_code="cold_start_category_based",
                        reason_text=f"Based on your browsing in {p.category}",
                        source="cold_start",
                    ))
                logger.info(
                    "Customer %s: served behavior-aware category cold start (top category=%s).",
                    customer_id, top_cat,
                )
                return _deduplicate_recommendations(result)

    # 7. Fallback: trending products (by view count in last 7 days)
    seven_days_ago = utcnow() - timedelta(days=7)
    trending_result = await db.execute(
        select(
            Product,
            func.count(Event.event_id).label("view_count"),
        )
        .join(Event, Event.product_id == Product.product_id)
        .where(
            Event.event_type == "page_view",
            Event.event_timestamp >= seven_days_ago,
        )
        .group_by(Product.product_id)
        .order_by(func.count(Event.event_id).desc())
        .limit(10)
    )
    trending = trending_result.all()

    if trending:
        result = []
        for idx, (p, _) in enumerate(trending):
            converted_price, cur, sym = convert_price(p.price, customer_currency)
            result.append(RecommendationOut(
                product_id=p.product_id,
                name=p.name,
                category=p.category or "",
                subcategory=p.subcategory,
                brand=p.brand,
                price=converted_price,
                currency=cur,
                symbol=sym,
                image_url=p.image_url,
                rating=p.rating,
                discount_percent=p.discount_percent,
                original_price=convert_original_price(p.original_price, customer_currency),
                score=1.0 / (idx + 1),
                reason_code="trending",
                reason_text="Popular item right now",
                source="popular",
            ))
        logger.info("Customer %s: served global trending fallback.", customer_id)
        return _deduplicate_recommendations(result)

    # 8. Empty fallback
    logger.info("Customer %s: no recommendations available.", customer_id)
    return []


async def _recent_category_interests(customer_id: str, db: AsyncSession) -> list[str]:
    """Top categories for a customer, weighted by their own behavioural events
    (purchases > cart > wishlist > clicks > views), most-preferred first.

    Serves the behavior-aware cold-start path when no model signal exists.
    """
    result = await db.execute(
        select(Event.product_id, Event.event_type).where(
            Event.customer_id == customer_id
        )
    )
    rows = result.all()
    pids = [r[0] for r in rows if r[0]]
    if not pids:
        return []

    prod_result = await db.execute(
        select(Product.product_id, Product.category).where(
            Product.product_id.in_(pids)
        )
    )
    prod_cat = {p.product_id: p.category for p in prod_result.all()}
    weights = {
        "purchase": 5.0,
        "add_to_cart": 3.0,
        "wishlist_add": 2.5,
        "email_click": 2.0,
        "page_view": 1.0,
        "email_open": 0.5,
    }
    cat_counts: dict[str, float] = {}
    for pid, etype in rows:
        cat = prod_cat.get(pid)
        if cat:
            cat_counts[cat] = cat_counts.get(cat, 0.0) + weights.get(etype, 1.0)
    return sorted(cat_counts, key=cat_counts.get, reverse=True)
