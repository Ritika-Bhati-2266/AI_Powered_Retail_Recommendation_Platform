"""
Customer endpoints.
GET  /api/customers/search?q=...
GET  /api/customers/{customer_id}
POST /api/customers
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_delete
from app.currency import get_available_currencies, price_to_usd
from app.database import get_db
from app.models import (
    ConsentLog,
    Customer,
    CustomerCategoryPreference,
    CustomerOffer,
    CustomerSegment,
    Event,
    Offer,
    Order,
    Product,
    Recommendation,
)
from app.privacy import ConsentService
from app.schemas import (
    CustomerCreate,
    CustomerMetrics,
    CustomerOut,
    CustomerSearchResult,
    CustomerUpdate,
    SegmentOut,
)
from app.security import hash_password, require_admin, require_owner
from app.utils import get_price_tier, utcnow

router = APIRouter(tags=["customers"])


@router.post("/customers", response_model=CustomerOut, status_code=201)
async def create_customer(
    payload: CustomerCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new customer, assign new_user segment, and assign matching offers."""
    # Deterministic duplicate check before any write, so even a pre-existing DB
    # without the email unique index reports a clean 409 instead of a 500 or a
    # silent double-insert.
    existing = await db.execute(
        select(Customer.customer_id).where(func.lower(Customer.email) == payload.email.strip().lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="An account with this email address already exists.",
        )

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
        password_hash=hash_password(payload.password),
        created_at=now,
    )

    try:
        db.add(customer)

        # Assign new_user segment immediately (bypasses metrics-based
        # evaluation) — but only for consenting accounts, mirroring the guard
        # in OfferEngine.assign_segments so non-consenting customers stay
        # unsegmented.
        if payload.consent_given:
            db.add(CustomerSegment(
                customer_id=customer_id,
                segment="new_user",
                assigned_at=now,
            ))

        # Assign offers matching the new_user segment
        result = await db.execute(
            select(Offer).where(
                Offer.segment == "new_user",
                Offer.is_active,
                Offer.valid_from <= now,
                Offer.valid_until >= now,
            )
        )
        welcome_offer = result.scalar_one_or_none()
        if payload.consent_given and welcome_offer:
            db.add(CustomerOffer(
                customer_id=customer_id,
                offer_id=welcome_offer.offer_id,
                assigned_at=now,
            ))

        # Store cold-start category preferences if provided. Only categories that
        # actually exist in the product catalog are meaningful — derive the allowed
        # set from the DB so signup chips always match the catalog (previously a
        # hardcoded list like "Sports"/"Beauty" never matched real categories such
        # as "Sports & Outdoors", silently killing cold-start recommendations).
        result = await db.execute(
            select(Product.category)
            .distinct()
            .where(Product.category.isnot(None))
        )
        valid_categories = {row[0] for row in result.all()}
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
        ) from None

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
    auth: Customer = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only lookup of a customer by email. Self-service login uses /api/auth/login."""
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
    admin: Customer = Depends(require_admin),
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
    auth: Customer = Depends(require_owner),
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

    # Consent grant/revoke (privacy guardrail). Persist the new state, timestamp
    # it, log the action as an audit trail, and invalidate any cached
    # personalisation so a revocation takes effect immediately.
    if payload.consent_given is not None and payload.consent_given != customer.consent_given:
        customer.consent_given = payload.consent_given
        customer.consent_timestamp = utcnow()
        consent_service = ConsentService(db)
        await consent_service.log_consent(
            customer_id,
            action="granted" if payload.consent_given else "revoked",
            dp_act="GDPR",
        )
        if payload.consent_given:
            # Re-enabling consent restores personalisation: re-evaluate the
            # segment set and re-assign any matching active offers so the
            # customer isn't stuck without offers until an admin re-runs
            # assign-offers.
            from app.offers import OfferEngine
            engine = OfferEngine(db)
            await engine.assign_segments(customer_id)
            segment_result = await db.execute(
                select(CustomerSegment.segment).where(
                    CustomerSegment.customer_id == customer_id
                )
            )
            segment_names = [row[0] for row in segment_result.all()]
            now = utcnow()
            if segment_names:
                offers_result = await db.execute(
                    select(Offer).where(
                        Offer.segment.in_(segment_names),
                        Offer.is_active,
                        Offer.valid_from <= now,
                        Offer.valid_until >= now,
                    )
                )
                for offer in offers_result.scalars().all():
                    db.add(CustomerOffer(
                        customer_id=customer_id,
                        offer_id=offer.offer_id,
                        assigned_at=now,
                    ))
        else:
            # Revocation purges all personalisation state so no stale
            # segment/offer rows survive to keep serving behavioural targeting
            # (the right-to-forget path already does this; a plain revoke must
            # too — otherwise checkout could still apply a stale discount while
            # the UI claims personalisation is off).
            await db.execute(
                delete(CustomerSegment).where(CustomerSegment.customer_id == customer_id)
            )
            await db.execute(
                delete(CustomerOffer).where(CustomerOffer.customer_id == customer_id)
            )
        await cache_delete(f"recs:{customer_id}")

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
    auth: Customer = Depends(require_owner),
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


@router.get("/customers/{customer_id}/data-export")
async def export_customer_data(
    customer_id: str,
    auth: Customer = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    """
    GDPR/DPDP Right of Access — return every piece of personal data held about a
    customer (profile, category prefs, segments, events, recommendations,
    offers, orders and consent audit trail) as a portable JSON document.
    Self-only unless the caller is an admin.
    """
    customer_result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    category_result = await db.execute(
        select(CustomerCategoryPreference.category)
        .where(CustomerCategoryPreference.customer_id == customer_id)
        .order_by(CustomerCategoryPreference.category)
    )
    category_preferences = list(category_result.scalars().all())

    segment_result = await db.execute(
        select(CustomerSegment)
        .where(CustomerSegment.customer_id == customer_id)
        .order_by(CustomerSegment.assigned_at)
    )
    segments = segment_result.scalars().all()

    event_result = await db.execute(
        select(Event).where(Event.customer_id == customer_id).order_by(Event.event_timestamp)
    )
    events = event_result.scalars().all()

    rec_result = await db.execute(
        select(Recommendation).where(Recommendation.customer_id == customer_id)
    )
    recommendations = rec_result.scalars().all()

    offer_result = await db.execute(
        select(Offer, CustomerOffer)
        .join(CustomerOffer, CustomerOffer.offer_id == Offer.offer_id)
        .where(CustomerOffer.customer_id == customer_id)
    )
    offers = offer_result.all()

    order_result = await db.execute(
        select(Order).where(Order.customer_id == customer_id).order_by(Order.created_at)
    )
    orders = order_result.scalars().all()

    consent_result = await db.execute(
        select(ConsentLog).where(ConsentLog.customer_id == customer_id).order_by(ConsentLog.timestamp)
    )
    consent_logs = consent_result.scalars().all()

    return {
        "exported_at": utcnow().isoformat(),
        "customer": {
            "customer_id": customer.customer_id,
            "name": customer.name,
            "email": customer.email,
            "consent_status": customer.consent_given,
            "consent_timestamp": customer.consent_timestamp,
            "forgotten_at": customer.forgotten_at,
            "currency": customer.currency,
            "role": customer.role,
            "created_at": customer.created_at,
        },
        "category_preferences": category_preferences,
        "segments": [
            {"segment": s.segment, "assigned_at": s.assigned_at.isoformat()}
            for s in segments
        ],
        "events": [
            {
                "event_id": e.event_id,
                "product_id": e.product_id,
                "event_type": e.event_type,
                "session_id": e.session_id,
                "metadata": e.event_metadata,
                "event_timestamp": e.event_timestamp.isoformat(),
            }
            for e in events
        ],
        "recommendations": [
            {
                "product_id": r.product_id,
                "score": r.score,
                "reason_code": r.reason_code,
                "reason_text": r.reason_text,
                "generated_at": r.generated_at.isoformat(),
            }
            for r in recommendations
        ],
        "offers": [
            {
                "offer_id": co.offer_id,
                "title": offer.title,
                "description": offer.description,
                "assigned_at": co.assigned_at.isoformat(),
            }
            for offer, co in offers
        ],
        "orders": [
            {
                "order_id": o.order_id,
                "total_amount": o.total_amount,
                "currency": o.currency,
                "status": o.status,
                "shipping_name": o.shipping_name,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ],
        "consent_audit_trail": [
            {
                "action": log.action,
                "dp_act": log.dp_act,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in consent_logs
        ],
    }


@router.post("/customers/{customer_id}/forget")
async def forget_my_account(
    customer_id: str,
    auth: Customer = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    """Self-service GDPR/DPDP Right to Forget.

    Any customer may erase their own data (owner-scoped, admin not required).
    Reuses ConsentService.right_to_forget: deletes behavioural data, anonymises
    order PII, and stamps `forgotten_at` so the caller's own bearer token is
    invalidated immediately. The client should log the user out afterwards.
    """
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    consent_service = ConsentService(db)
    await consent_service.right_to_forget(customer_id)
    await db.commit()

    return {"status": "forgotten", "message": "Your data has been erased. Log out and sign up again if you wish to return."}


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

    # Purchase facts come from the orders table (server-authoritative) rather
    # than purchase events — a purchase event is emitted per line item, so
    # counting those events would report line items, not orders.
    order_count_result = await db.execute(
        select(func.count(Order.order_id)).where(Order.customer_id == customer_id)
    )
    total_purchases = order_count_result.scalar() or 0

    # Lifetime value (NET spend, normalised to USD). Each order's total_amount
    # already has the applied checkout discount subtracted, so summing order
    # totals (converted back to USD from the order's display currency) reports
    # what the customer actually paid — same USD basis as the segment engine
    # (offers.py) so the two metric computations can never disagree.
    lv_result = await db.execute(
        select(Order.currency, Order.total_amount)
        .where(Order.customer_id == customer_id)
    )
    lifetime_value = round(
        sum(
            price_to_usd(total_amount or 0.0, currency)
            for currency, total_amount in lv_result.all()
        ),
        2,
    )

    if not events:
        return CustomerMetrics(
            total_purchases=total_purchases,
            lifetime_value=lifetime_value,
        )

    # Count by type
    event_types = {}
    for ev in events:
        event_types[ev.event_type] = event_types.get(ev.event_type, 0) + 1

    total_views = event_types.get("page_view", 0)
    total_cart_events = event_types.get("add_to_cart", 0) + event_types.get("remove_from_cart", 0)
    total_email_engagement = event_types.get("email_open", 0) + event_types.get("email_click", 0)

    # Session duration (approximate) — average minutes per session
    session_durations = []
    sessions: dict[str, list] = {}
    for e in events:
        if e.session_id:
            sessions.setdefault(e.session_id, []).append(e.event_timestamp)
    for timestamps in sessions.values():
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
        lifetime_value=lifetime_value,
        preferred_category=preferred_category,
        preferred_price_tier=preferred_price_tier,
    )
