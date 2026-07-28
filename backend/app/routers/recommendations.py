"""Recommendations endpoint.
GET /api/customers/{customer_id}/recommendations
"""
import json
import pandas as pd
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Customer, Event, Product, Recommendation, CustomerSegment
from app.schemas import RecommendationOut
from app.privacy import ConsentService
from app.config import settings
from app.utils import utcnow
from app.currency import convert_price
from app.models import CustomerCategoryPreference
from app.cache import cache_get, cache_set

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
    return rec


@router.get("/customers/{customer_id}/recommendations", response_model=list[RecommendationOut])
async def get_recommendations(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get top 10 personalised recommendations for a customer."""
    # Try cache first
    cache_key = f"recs:{customer_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        try:
            data = json.loads(cached)
            return [RecommendationOut(**item) for item in data]
        except Exception:
            pass

    # 1. Check consent
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

    # 3. Check event count for this customer (used to decide cold-start vs model)
    event_count_result = await db.execute(
        select(func.count(Event.event_id))
        .where(Event.customer_id == customer_id)
    )
    customer_event_count = event_count_result.scalar() or 0

    # 4. Cold-start: use signup category preferences for new customers with no events
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
                        original_price=p.original_price,
                        score=1.0 / (idx + 1),
                        reason_code="cold_start",
                        reason_text=f"Based on your interest in {p.category}",
                    ))
                if result:
                    return _deduplicate_recommendations(result)

    # 5. Try model-based recommendations (only for customers with events)
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
                        original_price=product.original_price,
                        score=rec.score,
                        reason_code=rec.reason_code or "top_pick",
                        reason_text=rec.reason_text or "Recommended for you",
                    ))
            if recommendations:
                deduped = _deduplicate_recommendations(recommendations)
                try:
                    await cache_set(cache_key, json.dumps([r.model_dump() for r in deduped], default=str), ttl=300)
                except Exception:
                    pass
                return deduped

        # Fallback: use the in-memory model to generate live recommendations
        try:
            # Build events and products DataFrames for the recommender
            events_result = await db.execute(select(Event))
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
                return _deduplicate_recommendations(live_recs)
        except Exception as e:
            # Log but fall through to trending
            import logging
            logging.getLogger(__name__).warning(f"Live recommendation failed: {e}")

    # 6. Fallback: trending products (by view count in last 7 days)
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
                original_price=p.original_price,
                score=1.0 / (idx + 1),
                reason_code="trending",
                reason_text="Popular item right now",
            ))
        return _deduplicate_recommendations(result)

    # 7. Empty fallback
    return []
