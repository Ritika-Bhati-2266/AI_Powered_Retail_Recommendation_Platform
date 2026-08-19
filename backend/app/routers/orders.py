"""
Order / checkout endpoints.
POST /api/customers/{customer_id}/orders   -- place an order
GET  /api/customers/{customer_id}/orders   -- order history (newest first)
GET  /api/customers/{customer_id}/orders/{order_id} -- order detail
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.currency import convert_price
from app.database import get_db
from app.models import Customer, Event, Order, OrderItem, Product
from app.offers import OfferEngine
from app.schemas import OrderCreate, OrderItemOut, OrderOut
from app.security import require_owner
from app.utils import utcnow

router = APIRouter(tags=["orders"])


async def _get_items_for_order(db: AsyncSession, order: Order) -> list[OrderItem]:
    result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order.order_id)
    )
    return list(result.scalars().all())


async def _order_out(db: AsyncSession, order: Order) -> OrderOut:
    items = await _get_items_for_order(db, order)
    return OrderOut(
        order_id=order.order_id,
        customer_id=order.customer_id,
        total_amount=order.total_amount,
        currency=order.currency,
        applied_offer_id=order.applied_offer_id,
        discount_amount=order.discount_amount or 0.0,
        status=order.status,
        shipping_name=order.shipping_name,
        shipping_address=order.shipping_address,
        created_at=order.created_at,
        items=[
            OrderItemOut(
                order_item_id=i.order_item_id,
                product_id=i.product_id,
                product_name_snapshot=i.product_name_snapshot,
                quantity=i.quantity,
                unit_price=i.unit_price,
                subtotal=i.subtotal,
            )
            for i in items
        ],
    )


@router.post("/customers/{customer_id}/orders", response_model=OrderOut, status_code=201)
async def place_order(
        customer_id: str,
        payload: OrderCreate,
        auth: Customer = Depends(require_owner),
        db: AsyncSession = Depends(get_db),
    ):
    """Place an order from cart line items. Prices are computed server-side
    from the actual product prices (client-sent prices are ignored). Any
    assigned offer whose minimum-purchase threshold is met is applied to the
    subtotal before the final total is stored, so the discount a customer sees
    is the discount they actually get. Also emits a `purchase` event per line
    item so it feeds the recommender and segmentation systems."""
    cust_result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    currency = customer.currency or "USD"
    now = utcnow()
    order = Order(
        order_id=str(uuid.uuid4()),
        customer_id=customer_id,
        total_amount=0.0,
        currency=currency,
        applied_offer_id=None,
        discount_amount=0.0,
        status="placed",
        shipping_name=payload.shipping_name,
        shipping_address=payload.shipping_address,
        created_at=now,
    )
    db.add(order)

    # Resolve products and compute server-side subtotals (client prices are
    # ignored). Line snapshots are collected first so the offer discount below
    # is computed against the customer's pre-purchase behaviour metrics.
    lines = []
    subtotal_total = 0.0
    for line in payload.items:
        prod_result = await db.execute(
            select(Product).where(Product.product_id == line.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product not found: {line.product_id}")

        unit_price, _, _ = convert_price(product.price, currency)
        subtotal = round(unit_price * line.quantity, 2)
        subtotal_total += subtotal
        lines.append((product, unit_price, line.quantity, subtotal))

    # Apply the best applicable assigned offer (min-purchase gated). Both the
    # subtotal and discount are in the customer's display currency, so the
    # stored total matches what the customer is shown.
    discount = await OfferEngine(db).get_checkout_discount(customer_id, currency, subtotal_total)
    if discount:
        order.applied_offer_id = discount["offer_id"]
        order.discount_amount = discount["discount_amount"]

    for product, unit_price, quantity, subtotal in lines:
        db.add(OrderItem(
            order_item_id=str(uuid.uuid4()),
            order_id=order.order_id,
            product_id=product.product_id,
            product_name_snapshot=product.name,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal,
        ))

        # Emit a purchase event so the recommender/segment engine sees this
        # activity — but only for consenting customers (privacy guardrail:
        # behaviour events are never tracked without opt-in).
        if customer.consent_given:
            db.add(Event(
                event_id=str(uuid.uuid4()),
                customer_id=customer_id,
                product_id=product.product_id,
                event_type="purchase",
                session_id=None,
                event_timestamp=now,
            ))

    order.total_amount = round(subtotal_total - (order.discount_amount or 0.0), 2)
    await db.commit()
    await db.refresh(order)

    return await _order_out(db, order)


@router.get("/customers/{customer_id}/orders", response_model=list[OrderOut])
async def get_order_history(
    customer_id: str,
    auth: Customer = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    """Return order history for a customer, newest first."""
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Customer not found")

    orders_result = await db.execute(
        select(Order)
        .where(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
    )
    orders = orders_result.scalars().all()
    return [await _order_out(db, o) for o in orders]


@router.get("/customers/{customer_id}/orders/{order_id}", response_model=OrderOut)
async def get_order_detail(
    customer_id: str,
    order_id: str,
    auth: Customer = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get a single order detail for a customer."""
    result = await db.execute(
        select(Order).where(
            Order.customer_id == customer_id,
            Order.order_id == order_id,
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return await _order_out(db, order)
