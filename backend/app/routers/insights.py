"""
Customer insights endpoints.
GET /api/customers/{customer_id}/recently-viewed
GET /api/customers/{customer_id}/continue-shopping
GET /api/customers/{customer_id}/wishlist
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Customer, Event, Product
from app.schemas import ProductSearchResult
from app.security import require_owner
from app.serializers import serialize_product

router = APIRouter(tags=["insights"])


async def _ensure_consent(customer: Customer) -> None:
    """Behaviour-driven insights must be unavailable once consent is absent."""
    if not customer.consent_given:
        raise HTTPException(
            status_code=403,
            detail="Customer has not given consent for personalisation. Insights are unavailable.",
        )


@router.get(
    "/customers/{customer_id}/recently-viewed",
    response_model=list[ProductSearchResult],
)
async def get_recently_viewed(
    customer_id: str,
    limit: int = 10,
    auth: Customer = Depends(require_owner),
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

    await _ensure_consent(customer)

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

    return [serialize_product(p, customer_currency) for p in products]


# Event types that add an item to / remove an item from the wishlist. The older
# generic "wishlist" type is still treated as an "add" for backward compatibility
# with events recorded before add/remove were distinguished.
WISHLIST_ADD_TYPES = ("wishlist", "wishlist_add")
WISHLIST_REMOVE_TYPES = ("wishlist_remove",)
WISHLIST_EVENT_TYPES = WISHLIST_ADD_TYPES + WISHLIST_REMOVE_TYPES


@router.get(
    "/customers/{customer_id}/wishlist",
    response_model=list[ProductSearchResult],
)
async def get_customer_wishlist(
    customer_id: str,
    limit: int = 50,
    auth: Customer = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get the customer's current wishlist.

    Wishlist state is derived from behaviour events: the most recent
    wishlist-affecting event per product decides whether the product is on the
    wishlist (a `wishlist_add`/`wishlist` puts it on, a `wishlist_remove` takes
    it off).
    """
    # Check customer exists
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    await _ensure_consent(customer)

    customer_currency = customer.currency or "USD"

    events = await db.execute(
        select(
            Event.product_id,
            Event.event_type,
            Event.event_timestamp,
        )
        .where(
            Event.customer_id == customer_id,
            Event.event_type.in_(WISHLIST_EVENT_TYPES),
            Event.product_id.isnot(None),
        )
        .order_by(Event.event_timestamp.asc())
    )
    latest_by_product: dict[str, str] = {
        pid: etype for pid, etype, _ts in events.all()
    }

    wishlisted_ids = [
        pid for pid, etype in latest_by_product.items()
        if etype in WISHLIST_ADD_TYPES
    ][:limit]

    if not wishlisted_ids:
        return []

    products_result = await db.execute(
        select(Product).where(Product.product_id.in_(wishlisted_ids))
    )
    products = products_result.scalars().all()
    order = {pid: i for i, pid in enumerate(wishlisted_ids)}
    products.sort(key=lambda p: order.get(p.product_id, 0))

    return [serialize_product(p, customer_currency) for p in products]


@router.get(
    "/customers/{customer_id}/continue-shopping",
    response_model=list[ProductSearchResult],
)
async def get_continue_shopping(
    customer_id: str,
    limit: int = 10,
    auth: Customer = Depends(require_owner),
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

    await _ensure_consent(customer)

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

    return [serialize_product(p, customer_currency) for p in products]
