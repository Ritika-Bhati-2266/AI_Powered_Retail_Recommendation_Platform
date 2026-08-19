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


def convert_original_price(original_price: float | None, currency: str) -> float | None:
    """Convert a USD original/strike-through price into ``currency``.

    Mirrors how ``price`` is converted so both fields render on the same scale
    with the same currency symbol — otherwise a non-USD customer sees a USD
    original price next to a converted price and the strike-through discount is
    never correct. ``None`` passes through unchanged.
    """
    if original_price is None:
        return None
    return convert_price(original_price, currency)[0]


def serialize_product(product, currency: str = "USD") -> ProductSearchResult:
    """Convert a Product ORM object into its API response shape, converting the
    price (and the original/strike-through price) into the given customer
    currency."""
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
        original_price=convert_original_price(product.original_price, currency),
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
