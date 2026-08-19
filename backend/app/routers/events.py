"""
Event ingestion endpoint.
POST /api/events — ingest a behaviour event.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Customer, Event, Product
from app.schemas import EventCreate, EventOut
from app.security import get_current_customer
from app.utils import utcnow

router = APIRouter(tags=["events"])


@router.post("/events", response_model=EventOut)
async def ingest_event(
    event_data: EventCreate,
    auth: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a customer behaviour event. Token-authenticated: the caller may
    only submit events for their own account (admins may submit for anyone)."""
    if auth.role != "admin" and event_data.customer_id != auth.customer_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: you can only submit events for your own account.",
        )

    # Validate customer exists
    customer = await db.execute(
        select(Customer).where(Customer.customer_id == event_data.customer_id)
    )
    customer_row = customer.scalar_one_or_none()
    if not customer_row:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Consent gate (privacy guardrail): do not record behavioural events for a
    # customer who has not given consent for personalisation. Personal tracking
    # must only ever happen for consenting users.
    if not customer_row.consent_given:
        raise HTTPException(
            status_code=403,
            detail="Customer has not given consent for personalisation. Behavioural events are not tracked.",
        )

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

    # Re-evaluate the customer's segment membership now that their behaviour has
    # changed, so segments stay current. (Offers are recomputed at startup and
    # via POST /api/admin/assign-offers.)
    from app.offers import OfferEngine
    await OfferEngine(db).assign_segments(event_data.customer_id)
    await db.flush()

    return EventOut(event_id=event.event_id)
