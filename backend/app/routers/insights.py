"""
Customer insights endpoints.
GET /api/customers/{customer_id}/recently-viewed
GET /api/customers/{customer_id}/continue-shopping
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_, not_, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Customer, Event, Product
from app.schemas import ProductSearchResult
from app.currency import convert_price

router = APIRouter(tags=["insights"])


@router.get(
    "/customers/{customer_id}/recently-viewed",
    response_model=list[ProductSearchResult],
)
async def get_recently_viewed(
    customer_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Get the last N distinct products viewed by a customer."""
    # Check customer exists
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer_currency = customer.currency or "USD"

    # Get distinct page_view product_ids ordered by most recent
    # Subquery: find max timestamp per product per customer for page_views
    subq = (
        select(
            Event.product_id,
            func.max(Event.event_timestamp).label("last_viewed"),
        )
        .where(
            Event.customer_id == customer_id,
            Event.event_type == "page_view",
            Event.product_id.isnot(None),
        )
        .group_by(Event.product_id)
        .order_by(func.max(Event.event_timestamp).desc())
        .limit(limit)
        .subquery()
    )

    stmt = select(Product).join(
        subq, Product.product_id == subq.c.product_id
    )

    result = await db.execute(stmt)
    products = result.scalars().all()

    out = []
    for p in products:
        converted_price, cur, sym = convert_price(p.price, customer_currency)
        out.append(ProductSearchResult(
            product_id=p.product_id,
            name=p.name,
            category=p.category or "",
            subcategory=p.subcategory or "",
            brand=p.brand or "",
            price=converted_price,
            currency=cur,
            symbol=sym,
            image_url=p.image_url or "",
            rating=p.rating,
            discount_percent=p.discount_percent,
            original_price=p.original_price,
        ))
    return out


@router.get(
    "/customers/{customer_id}/continue-shopping",
    response_model=list[ProductSearchResult],
)
async def get_continue_shopping(
    customer_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Get products the customer added to cart but hasn't purchased yet."""
    # Check customer exists
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer_currency = customer.currency or "USD"

    # Find products that have add_to_cart but no purchase for this customer
    # Products that were added to cart
    cart_subq = (
        select(Event.product_id)
        .where(
            Event.customer_id == customer_id,
            Event.event_type == "add_to_cart",
            Event.product_id.isnot(None),
        )
        .distinct()
        .subquery()
    )

    # Products that were purchased (to exclude)
    purchase_subq = (
        select(Event.product_id)
        .where(
            Event.customer_id == customer_id,
            Event.event_type == "purchase",
            Event.product_id.isnot(None),
        )
        .distinct()
        .subquery()
    )

    stmt = (
        select(Product)
        .where(
            Product.product_id.in_(select(cart_subq.c.product_id)),
            ~Product.product_id.in_(select(purchase_subq.c.product_id)),
        )
        .order_by(Product.name)
        .limit(limit)
    )

    result = await db.execute(stmt)
    products = result.scalars().all()

    out = []
    for p in products:
        converted_price, cur, sym = convert_price(p.price, customer_currency)
        out.append(ProductSearchResult(
            product_id=p.product_id,
            name=p.name,
            category=p.category or "",
            subcategory=p.subcategory or "",
            brand=p.brand or "",
            price=converted_price,
            currency=cur,
            symbol=sym,
            image_url=p.image_url or "",
            rating=p.rating,
            discount_percent=p.discount_percent,
            original_price=p.original_price,
        ))
    return out
