"""One-time migration: update existing products with real picsum.photos image URLs."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select

from app.database import async_session_factory, create_tables
from app.models import Product
from app.seed_data import get_product_image_url


async def main():
    await create_tables()
    async with async_session_factory() as db:
        result = await db.execute(select(Product).order_by(Product.created_at))
        products = result.scalars().all()

        count = 0
        for product in products:
            new_url = get_product_image_url(product.product_id, product.category or "", product.subcategory or "", product.name or "")
            if product.image_url != new_url:
                product.image_url = new_url
                count += 1

        await db.commit()
        print(f"Updated {count} product image URLs.")
        print(f"Total products: {len(products)}")


if __name__ == "__main__":
    asyncio.run(main())
