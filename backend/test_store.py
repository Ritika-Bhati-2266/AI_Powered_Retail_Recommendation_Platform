"""Test _store_recommendations logic directly."""
import sys; sys.path.insert(0, '.')
import asyncio
import pandas as pd
from app.config import settings
from app.recommender import RecommendationEngine
from app.database import async_session_factory
from app.models import Customer, Recommendation, Event, Product
from sqlalchemy import select, delete, func

async def test():
    # Load the trained model
    engine = RecommendationEngine(settings)
    loaded = engine.load()
    print(f"Engine loaded: {loaded}")
    print(f"Is trained: {engine._is_trained}")
    print(f"User count: {len(engine._user_ids)}")
    print(f"Item count: {len(engine._item_ids)}")
    print(f"Product details: {len(engine._product_details)}")

    async with async_session_factory() as db:
        # Get consenting customers
        result = await db.execute(select(Customer).where(Customer.consent_given == True))
        customers = result.scalars().all()
        print(f"\nConsenting customers: {len(customers)}")

        # Test recommend for first customer
        if customers:
            c = customers[0]
            print(f"\nTesting recommend for {c.customer_id}")
            recs = engine.recommend(customer_id=c.customer_id, n=10)
            print(f"Got {len(recs)} recommendations")
            if recs:
                for r in recs[:3]:
                    print(f"  {r['name']} score={r['score']:.3f} reason={r['reason_code']}")
            else:
                print("  No recommendations returned!")

        # Now try the full _store_recommendations flow
        print("\n--- Testing _store_recommendations flow ---")
        
        # Get all customers with consent
        result = await db.execute(select(Customer).where(Customer.consent_given == True))
        customers = result.scalars().all()
        if not customers:
            print("No consenting customers!")
            return

        # Clear old recommendations
        await db.execute(delete(Recommendation))
        print(f"Cleared old recommendations")

        from app.utils import utcnow
        now = utcnow()
        stored = 0

        for customer in customers:
            try:
                recs = engine.recommend(customer_id=customer.customer_id, n=10)
                if not recs:
                    continue

                # Fetch product data
                prod_result = await db.execute(select(Product))
                all_products = prod_result.scalars().all()
                products_df = pd.DataFrame([
                    {"product_id": p.product_id, "category": p.category}
                    for p in all_products
                ])

                # Fetch customer events
                events_result = await db.execute(
                    select(Event).where(Event.customer_id == customer.customer_id)
                )
                customer_events = events_result.scalars().all()

                for rec in recs:
                    events_list = [
                        {"customer_id": e.customer_id, "product_id": e.product_id, "event_type": e.event_type}
                        for e in customer_events
                    ]
                    interactions_df = pd.DataFrame(events_list) if events_list else pd.DataFrame()

                    reason_code = rec.get("reason_code", "popular")
                    reason_text = rec.get("reason_text", "Popular item")

                    if not interactions_df.empty and not products_df.empty:
                        try:
                            rc, rt = engine.get_reason_code(
                                customer.customer_id,
                                rec["product_id"],
                                interactions_df,
                                products_df,
                            )
                            reason_code = rc
                            reason_text = rt
                        except Exception:
                            pass

                    recommendation = Recommendation(
                        customer_id=customer.customer_id,
                        product_id=rec["product_id"],
                        score=rec["score"],
                        reason_code=reason_code,
                        reason_text=reason_text,
                        generated_at=now,
                    )
                    db.add(recommendation)
                    stored += 1

            except Exception as e:
                print(f"  Failed for {customer.customer_id[:20]}: {type(e).__name__}: {e}")

        await db.commit()
        print(f"\nStored {stored} recommendations total")

        # Verify
        result = await db.execute(select(func.count(Recommendation.customer_id)))
        print(f"Verified in DB: {result.scalar()} recommendations")

if __name__ == "__main__":
    asyncio.run(test())
