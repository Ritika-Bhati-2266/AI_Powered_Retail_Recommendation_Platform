"""
Shared serializers and small DB helpers used across routers.

Centralises product -> API response conversion so that every router (products,
insights, etc.) builds responses through one code path instead of duplicating
the field mapping inline.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.currency import convert_price
from app.models import Customer
from app.schemas import ProductSearchResult


def serialize_product(product, currency: str = "USD") -> ProductSearchResult:
    """Convert a Product ORM object into its API response shape, converting the
    price into the given customer currency."""
    converted_price, cur, sym = convert_price(product.price, currency)
    return ProductSearchResult(
        product_id=product.product_id,
        name=product.name,
        category=product.category or "",
        subcategory=product.subcategory or "",
        brand=product.brand or "",
        price=converted_price,
        currency=cur,
        symbol=sym,
        image_url=product.image_url or "",
        rating=product.rating,
        discount_percent=product.discount_percent,
        original_price=product.original_price,
    )


async def resolve_customer_currency(db: AsyncSession, customer_id: str) -> str:
    """Return the customer's preferred currency, defaulting to USD."""
    if not customer_id:
        return "USD"
    result = await db.execute(
        select(Customer.currency).where(Customer.customer_id == customer_id)
    )
    cur = result.scalar_one_or_none()
    return cur or "USD"
