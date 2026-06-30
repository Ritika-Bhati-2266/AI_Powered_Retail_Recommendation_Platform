"""Run training directly to debug background task issues."""
import sys; sys.path.insert(0, '.')
import asyncio
import pandas as pd
from app.config import settings
from app.database import async_session_factory
from app.recommender import RecommendationEngine
from app.models import Event, Product, Customer
from sqlalchemy import select


async def train():
    print("Creating engine...")
    engine = RecommendationEngine(settings)

    print("Fetching events...")
    async with async_session_factory() as db:
        result = await db.execute(select(Event))
        events = result.scalars().all()
        print(f"Got {len(events)} events")

        result = await db.execute(select(Product))
        products = result.scalars().all()
        print(f"Got {len(products)} products")

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
        products_data = [
            {
                "product_id": p.product_id,
                "name": p.name,
                "category": p.category,
                "subcategory": p.subcategory,
                "brand": p.brand,
                "price": p.price,
                "image_url": p.image_url,
            }
            for p in products
        ]

        events_df = pd.DataFrame(events_data)
        products_df = pd.DataFrame(products_data)

        print("Training model...")
        engine.train(events_df, products_df, n_components=30)
        print("Training complete!")

        # Verify
        result = await db.execute(select(Customer).limit(1))
        customer = result.scalar_one()
        print(f"Testing recs for {customer.customer_id}")
        recs = engine.recommend(
            customer.customer_id, n=5,
            events_df=events_df, products_df=products_df
        )
        for r in recs:
            print(f"  {r['name']} (score={r['score']:.3f}, reason={r['reason_code']})")


if __name__ == "__main__":
    asyncio.run(train())
