"""
Event ingestion endpoint.
POST /api/events — ingest a behaviour event.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Event, Customer, Product
from app.schemas import EventCreate, EventOut
from app.utils import utcnow

router = APIRouter(tags=["events"])


@router.post("/events", response_model=EventOut)
async def ingest_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db),
):
    """Ingest a customer behaviour event."""
    # Validate customer exists
    customer = await db.execute(
        select(Customer).where(Customer.customer_id == event_data.customer_id)
    )
    if not customer.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Customer not found")

    # Validate product exists if provided
    if event_data.product_id:
        product = await db.execute(
            select(Product).where(Product.product_id == event_data.product_id)
        )
        if not product.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Product not found")

    # Create event
    event = Event(
        event_id=str(uuid.uuid4()),
        customer_id=event_data.customer_id,
        product_id=event_data.product_id,
        event_type=event_data.event_type,
        session_id=event_data.session_id,
        event_metadata=event_data.metadata,
        event_timestamp=utcnow(),
    )
    db.add(event)
    await db.flush()

    return EventOut(event_id=event.event_id)
