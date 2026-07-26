"""
Customer endpoints.
GET  /api/customers/search?q=...
GET  /api/customers/{customer_id}
POST /api/customers
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Customer, Event, Product, CustomerSegment, CustomerOffer, Offer, CustomerCategoryPreference
from app.offers import OfferEngine
from app.schemas import CustomerOut, CustomerCreate, CustomerUpdate, CustomerSearchResult, CustomerMetrics, SegmentOut
from app.utils import utcnow, get_price_tier
from app.currency import convert_price, get_available_currencies

router = APIRouter(tags=["customers"])


@router.post("/customers", response_model=CustomerOut, status_code=201)
async def create_customer(
    payload: CustomerCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new customer, assign new_user segment, and assign matching offers."""
    # Create customer
    now = utcnow()
    customer_id = str(uuid.uuid4())
    email = payload.email or f"{payload.name.lower().replace(' ', '.')}@example.com"

    # Validate currency
    valid_currencies = get_available_currencies()
    currency = payload.currency if payload.currency in valid_currencies else "USD"

    customer = Customer(
        customer_id=customer_id,
        name=payload.name,
        email=email,
        consent_given=payload.consent_given,
        consent_timestamp=now if payload.consent_given else None,
        currency=currency,
        created_at=now,
    )

    try:
        db.add(customer)

        # Assign new_user segment immediately (bypasses metrics-based evaluation)
        db.add(CustomerSegment(
            customer_id=customer_id,
            segment="new_user",
            assigned_at=now,
        ))

        # Assign offers matching the new_user segment
        result = await db.execute(
            select(Offer).where(
                Offer.segment == "new_user",
                Offer.is_active == True,
                Offer.valid_from <= now,
                Offer.valid_until >= now,
            )
        )
        welcome_offer = result.scalar_one_or_none()
        if welcome_offer:
            db.add(CustomerOffer(
                customer_id=customer_id,
                offer_id=welcome_offer.offer_id,
                assigned_at=now,
            ))

        # Store cold-start category preferences if provided
        valid_categories = [
            "Electronics", "Clothing", "Home & Kitchen", "Books",
            "Sports", "Beauty", "Toys", "Grocery",
        ]
        for cat in payload.category_preferences:
            if cat in valid_categories:
                db.add(CustomerCategoryPreference(
                    customer_id=customer_id,
                    category=cat,
                    created_at=now,
                ))

        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account with this email address already exists.",
        )

    # Return full profile
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one()

    segment_result = await db.execute(
        select(CustomerSegment)
        .where(CustomerSegment.customer_id == customer_id)
        .order_by(CustomerSegment.assigned_at.desc())
    )
    segments = segment_result.scalars().all()

    cat_prefs = await _get_category_preferences(customer_id, db)
    metrics = await _compute_customer_metrics(customer_id, db)

    return CustomerOut(
        customer_id=customer.customer_id,
        name=customer.name,
        email=customer.email,
        consent_status=customer.consent_given,
        currency=customer.currency or "USD",
        role=customer.role or "customer",
        segments=[SegmentOut(segment=s.segment, assigned_at=s.assigned_at) for s in segments],
        category_preferences=cat_prefs,
        metrics=metrics,
    )


@router.get("/customers/by-email", response_model=CustomerOut)
async def get_customer_by_email(
    email: str = Query(..., description="Customer email address"),
    db: AsyncSession = Depends(get_db),
):
    """Look up a customer by email. Used for customer-facing login."""
    result = await db.execute(
        select(Customer).where(func.lower(Customer.email) == email.strip().lower())
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="No customer found with that email")

    # Get segments
    segment_result = await db.execute(
        select(CustomerSegment)
        .where(CustomerSegment.customer_id == customer.customer_id)
        .order_by(CustomerSegment.assigned_at.desc())
    )
    segments = segment_result.scalars().all()

    cat_prefs = await _get_category_preferences(customer.customer_id, db)
    metrics = await _compute_customer_metrics(customer.customer_id, db)

    return CustomerOut(
        customer_id=customer.customer_id,
        name=customer.name,
        email=customer.email,
        consent_status=customer.consent_given,
        currency=customer.currency or "USD",
        role=customer.role or "customer",
        segments=[SegmentOut(segment=s.segment, assigned_at=s.assigned_at) for s in segments],
        category_preferences=cat_prefs,
        metrics=metrics,
    )


@router.get("/customers/search", response_model=list[CustomerSearchResult])
async def search_customers(
    q: str = Query(..., min_length=1, description="Search query for name or email"),
    skip: int = Query(default=0, ge=0, description="Number of results to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    db: AsyncSession = Depends(get_db),
):
    """Search customers by name or email using case-insensitive matching."""
    pattern = f"%{q.lower()}%"
    result = await db.execute(
        select(Customer)
        .where(
            or_(
                func.lower(Customer.name).like(pattern),
                func.lower(Customer.email).like(pattern),
            )
        )
        .offset(skip)
        .limit(limit)
        .order_by(Customer.name)
    )
    customers = result.scalars().all()
    return [
        CustomerSearchResult(
            customer_id=c.customer_id,
            name=c.name,
            email=c.email,
            currency=c.currency or "USD",
        )
        for c in customers
    ]


@router.get("/customers/currencies")
async def get_currencies():
    """Return available currencies for the selector UI."""
    return get_available_currencies()


@router.patch("/customers/{customer_id}", response_model=CustomerOut)
async def update_customer_settings(
    customer_id: str,
    payload: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update customer settings (e.g. currency preference)."""
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if payload.currency is not None:
        valid_currencies = get_available_currencies()
        if payload.currency not in valid_currencies:
            raise HTTPException(status_code=400, detail=f"Invalid currency. Valid: {', '.join(valid_currencies.keys())}")
        customer.currency = payload.currency

    await db.commit()
    await db.refresh(customer)

    # Return full profile
    segment_result = await db.execute(
        select(CustomerSegment)
        .where(CustomerSegment.customer_id == customer_id)
        .order_by(CustomerSegment.assigned_at.desc())
    )
    segments = segment_result.scalars().all()

    cat_prefs = await _get_category_preferences(customer_id, db)
    metrics = await _compute_customer_metrics(customer_id, db)

    return CustomerOut(
        customer_id=customer.customer_id,
        name=customer.name,
        email=customer.email,
        consent_status=customer.consent_given,
        currency=customer.currency or "USD",
        role=customer.role or "customer",
        segments=[SegmentOut(segment=s.segment, assigned_at=s.assigned_at) for s in segments],
        category_preferences=cat_prefs,
        metrics=metrics,
    )


@router.get("/customers/{customer_id}", response_model=CustomerOut)
async def get_customer_profile(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full customer profile with metrics and segments."""
    # Get customer
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get segments
    segment_result = await db.execute(
        select(CustomerSegment)
        .where(CustomerSegment.customer_id == customer_id)
        .order_by(CustomerSegment.assigned_at.desc())
    )
    segments = segment_result.scalars().all()

    # Compute metrics
    cat_prefs = await _get_category_preferences(customer_id, db)
    metrics = await _compute_customer_metrics(customer_id, db)

    return CustomerOut(
        customer_id=customer.customer_id,
        name=customer.name,
        email=customer.email,
        consent_status=customer.consent_given,
        currency=customer.currency or "USD",
        role=customer.role or "customer",
        segments=[SegmentOut(segment=s.segment, assigned_at=s.assigned_at) for s in segments],
        category_preferences=cat_prefs,
        metrics=metrics,
    )


async def _get_category_preferences(customer_id: str, db: AsyncSession) -> list[str]:
    """Fetch stored category preferences for a customer."""
    result = await db.execute(
        select(CustomerCategoryPreference.category)
        .where(CustomerCategoryPreference.customer_id == customer_id)
        .order_by(CustomerCategoryPreference.category)
    )
    return list(result.scalars().all())


async def _compute_customer_metrics(customer_id: str, db: AsyncSession) -> CustomerMetrics:
    """Compute aggregated behavioural metrics for a customer."""
    now = utcnow()

    # Get all events
    result = await db.execute(
        select(Event).where(Event.customer_id == customer_id)
    )
    events = result.scalars().all()

    if not events:
        return CustomerMetrics()

    # Count by type
    event_types = {}
    for ev in events:
        event_types[ev.event_type] = event_types.get(ev.event_type, 0) + 1

    total_views = event_types.get("page_view", 0)
    total_purchases = event_types.get("purchase", 0)
    total_cart_events = event_types.get("add_to_cart", 0) + event_types.get("remove_from_cart", 0)
    total_email_engagement = event_types.get("email_open", 0) + event_types.get("email_click", 0)

    # Session duration (approximate) — average minutes per session
    session_durations = []
    sessions: dict[str, list] = {}
    for e in events:
        if e.session_id:
            sessions.setdefault(e.session_id, []).append(e.event_timestamp)
    for s_id, timestamps in sessions.items():
        if len(timestamps) >= 2:
            valid_ts = [t for t in timestamps if t is not None]
            if len(valid_ts) >= 2:
                duration = (max(valid_ts) - min(valid_ts)).total_seconds() / 60.0
                session_durations.append(duration)
    avg_session_duration = round(sum(session_durations) / len(session_durations), 2) if session_durations else 0.0

    # Days since last activity
    sorted_events = sorted(events, key=lambda e: e.event_timestamp or now, reverse=True)
    last_event_time = sorted_events[0].event_timestamp if sorted_events else now
    days_since_last = (now - last_event_time).days if last_event_time else 0

    # Lifetime value (sum of purchase prices)
    lifetime_value = 0.0
    purchase_product_ids = []
    for ev in events:
        if ev.event_type == "purchase" and ev.product_id:
            purchase_product_ids.append(ev.product_id)

    if purchase_product_ids:
        prod_result = await db.execute(
            select(Product).where(Product.product_id.in_(purchase_product_ids))
        )
        products = prod_result.scalars().all()
        lifetime_value = sum(p.price for p in products)

    # Preferred category (by most viewed/purchased)
    category_counts = {}
    product_ids = [ev.product_id for ev in events if ev.product_id]
    if product_ids:
        prod_result = await db.execute(
            select(Product).where(Product.product_id.in_(product_ids))
        )
        products = prod_result.scalars().all()
        for p in products:
            if p.category:
                category_counts[p.category] = category_counts.get(p.category, 0) + 1

    preferred_category = ""
    if category_counts:
        preferred_category = max(category_counts, key=category_counts.get)

    # Preferred price tier
    price_tier_counts = {}
    if product_ids:
        prod_result = await db.execute(
            select(Product).where(Product.product_id.in_(product_ids))
        )
        products = prod_result.scalars().all()
        for p in products:
            tier = get_price_tier(p.price)
            price_tier_counts[tier] = price_tier_counts.get(tier, 0) + 1

    preferred_price_tier = ""
    if price_tier_counts:
        preferred_price_tier = max(price_tier_counts, key=price_tier_counts.get)

    return CustomerMetrics(
        total_views=total_views,
        total_purchases=total_purchases,
        total_cart_events=total_cart_events,
        total_email_engagement=total_email_engagement,
        avg_session_duration_minutes=avg_session_duration,
        days_since_last_activity=abs(days_since_last),
        lifetime_value=round(lifetime_value, 2),
        preferred_category=preferred_category,
        preferred_price_tier=preferred_price_tier,
    )
