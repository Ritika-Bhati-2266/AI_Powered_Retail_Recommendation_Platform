"""
Event ingestion endpoint.
POST /api/events — ingest a behaviour event.
"""
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, get_db
from app.models import Customer, Event, Product
from app.schemas import EventCreate, EventOut
from app.security import get_current_customer
from app.utils import utcnow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["events"])


async def _recompute_customer_segments(customer_id: str) -> None:
    """Re-evaluate a customer's segment membership without blocking the ingest
    request.

    Scheduled as a FastAPI BackgroundTask on its own DB session (the request
    session is closed once the response is sent). Runs in-process after the
    response is delivered — an improvement over the previous synchronous
    recompute, but still not a distributed task queue: a production deployment
    should move this to a real scheduler/queue (APScheduler/Celery) as
    documented in the README.
    """
    try:
        from app.offers import OfferEngine

        async with async_session_factory() as session:
            await OfferEngine(session).assign_segments(customer_id)
            await session.commit()
    except Exception:  # background failure must not break the already-returned response
        logger.exception("Background segment recompute failed for customer %s", customer_id)


@router.post("/events", response_model=EventOut)
async def ingest_event(
    event_data: EventCreate,
    background_tasks: BackgroundTasks,
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

    # Defense-in-depth: `purchase` is already rejected at schema validation
    # (EventCreate.event_type is a strict Literal whitelist that excludes it).
    # This guard exists so the invariant survives any future schema loosening:
    # purchase events are created exclusively by the server during order
    # placement (routers/orders.py) and clients can never emit them directly.
    if event_data.event_type == "purchase":
        raise HTTPException(
            status_code=400,
            detail="Purchase events cannot be submitted directly.",
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
    # Persist the event before scheduling the background recompute so the
    # background task (which opens its own session) is guaranteed to see it.
    await db.commit()

    # Re-evaluate the customer's segment membership now that their behaviour has
    # changed — but in the background so the ingest response returns immediately
    # instead of waiting on the metrics queries + segment writes. (Offers are
    # recomputed at startup and via POST /api/admin/assign-offers.)
    background_tasks.add_task(_recompute_customer_segments, event_data.customer_id)

    return EventOut(event_id=event.event_id)
