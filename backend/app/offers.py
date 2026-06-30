"""
OfferEngine: segment assignment, offer management, and personalised offer delivery.
"""
import uuid
import logging
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomerSegment, Offer, CustomerOffer, Event, Product, Customer
from app.utils import utcnow

logger = logging.getLogger(__name__)

# ── Segment Definitions (hardcoded business rules) ───────────────────────────

SEGMENT_DEFINITIONS = {
    "high_value": {
        "label": "High Value",
        "description": "Lifetime value > 500 AND purchases > 5",
    },
    "bargain_hunter": {
        "label": "Bargain Hunter",
        "description": "Average price purchased < 30 AND purchase count > 3",
    },
    "new_user": {
        "label": "New User",
        "description": "Days since first event < 30",
    },
    "lapsed": {
        "label": "Lapsed",
        "description": "Days since last activity > 90",
    },
    "cart_abandoner": {
        "label": "Cart Abandoner",
        "description": "Cart events > purchase events AND cart events > 2",
    },
    "brand_loyalist": {
        "label": "Brand Loyalist",
        "description": "Purchases of single brand > 50% of total AND total purchases > 3",
    },
    "window_shopper": {
        "label": "Window Shopper",
        "description": "Views > 50 AND purchases = 0",
    },
    "power_user": {
        "label": "Power User",
        "description": "Events in last 30 days > 100",
    },
}

# ── Predefined Offers ────────────────────────────────────────────────────────

PREDEFINED_OFFERS = [
    {
        "title": "Welcome 15% Off",
        "description": "Welcome to our store! Enjoy 15% off your first purchase as a new member.",
        "discount_type": "percentage",
        "discount_value": 15,
        "segment": "new_user",
        "min_purchase": 0,
        "valid_days": 30,
    },
    {
        "title": "VIP Exclusive: 25% Off",
        "description": "As a valued VIP customer, enjoy 25% off your next order. Thank you for your loyalty!",
        "discount_type": "percentage",
        "discount_value": 25,
        "segment": "high_value",
        "min_purchase": 100,
        "valid_days": 45,
    },
    {
        "title": "Come Back! 20% Off",
        "description": "We miss you! Here's 20% off to welcome you back. Treat yourself!",
        "discount_type": "percentage",
        "discount_value": 20,
        "segment": "lapsed",
        "min_purchase": 0,
        "valid_days": 30,
    },
    {
        "title": "Complete Your Purchase: Free Shipping",
        "description": "Free shipping on your next order — complete what you started!",
        "discount_type": "fixed",
        "discount_value": 0,
        "segment": "cart_abandoner",
        "min_purchase": 0,
        "valid_days": 14,
    },
    {
        "title": "Bargain Bundle: Buy 2 Get 1 Free",
        "description": "Buy 2 items and get the 3rd free! Mix and match your favorites.",
        "discount_type": "percentage",
        "discount_value": 33,
        "segment": "bargain_hunter",
        "min_purchase": 0,
        "valid_days": 30,
    },
    {
        "title": "Brand Fan Bonus: 10% Extra Off",
        "description": "Loyalty pays! Enjoy an extra 10% off your favorite brand purchases.",
        "discount_type": "percentage",
        "discount_value": 10,
        "segment": "brand_loyalist",
        "min_purchase": 50,
        "valid_days": 30,
    },
    {
        "title": "Window Shopper Special: 10% Off First Purchase",
        "description": "We noticed you've been browsing! Here's 10% off your first purchase.",
        "discount_type": "percentage",
        "discount_value": 10,
        "segment": "window_shopper",
        "min_purchase": 0,
        "valid_days": 30,
    },
    {
        "title": "Power User Rewards: 15% Off Storewide",
        "description": "You're one of our most active shoppers! Enjoy 15% off everything storewide.",
        "discount_type": "percentage",
        "discount_value": 15,
        "segment": "power_user",
        "min_purchase": 0,
        "valid_days": 30,
    },
]


class OfferEngine:
    """Manages segment assignment and offer targeting."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def assign_segments(self, customer_id: str) -> list[str]:
        """
        Evaluate a customer against all segment definitions and assign
        matching segments. Returns list of assigned segment names.
        """
        # Gather customer metrics
        metrics = await self._compute_metrics(customer_id)
        assigned_segments = []

        # Evaluate each segment rule
        if metrics.get("lifetime_value", 0) > 500 and metrics.get("purchase_count", 0) > 5:
            assigned_segments.append("high_value")

        if metrics.get("avg_price_purchased", 999) < 30 and metrics.get("purchase_count", 0) > 3:
            assigned_segments.append("bargain_hunter")

        if metrics.get("days_since_first_event", 999) < 30:
            assigned_segments.append("new_user")

        if metrics.get("days_since_last_activity", 0) > 90:
            assigned_segments.append("lapsed")

        if (
            metrics.get("cart_events", 0) > metrics.get("purchase_events", 0)
            and metrics.get("cart_events", 0) > 2
        ):
            assigned_segments.append("cart_abandoner")

        if (
            metrics.get("top_brand_pct", 0) > 0.5
            and metrics.get("purchase_count", 0) > 3
        ):
            assigned_segments.append("brand_loyalist")

        if metrics.get("total_views", 0) > 50 and metrics.get("purchase_count", 0) == 0:
            assigned_segments.append("window_shopper")

        if metrics.get("events_30d", 0) > 100:
            assigned_segments.append("power_user")

        # Persist segment assignments
        # First clear old ones
        await self.db.execute(
            delete(CustomerSegment).where(CustomerSegment.customer_id == customer_id)
        )

        now = utcnow()
        for segment in assigned_segments:
            self.db.add(CustomerSegment(
                customer_id=customer_id,
                segment=segment,
                assigned_at=now,
            ))

        return assigned_segments

    async def _compute_metrics(self, customer_id: str) -> dict:
        """Compute behavioural metrics for a customer (used for segment evaluation)."""
        now = utcnow()
        thirty_days_ago = now - timedelta(days=30)
        ninety_days_ago = now - timedelta(days=90)

        # Get all events for this customer
        result = await self.db.execute(
            select(Event).where(Event.customer_id == customer_id)
        )
        events = result.scalars().all()

        total_events = len(events)
        if total_events == 0:
            return {
                "total_views": 0,
                "purchase_count": 0,
                "purchase_events": 0,
                "cart_events": 0,
                "total_views": 0,
                "lifetime_value": 0.0,
                "avg_price_purchased": 0.0,
                "days_since_first_event": 999,
                "days_since_last_activity": 999,
                "events_30d": 0,
                "top_brand_pct": 0.0,
            }

        purchase_events = [e for e in events if e.event_type == "purchase"]
        cart_events = [e for e in events if e.event_type in ("add_to_cart", "remove_from_cart")]
        view_events = [e for e in events if e.event_type == "page_view"]

        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.event_timestamp or now)

        first_event = sorted_events[0]
        last_event = sorted_events[-1]

        days_since_first = (now - first_event.event_timestamp).days if first_event.event_timestamp else 999
        days_since_last = (now - last_event.event_timestamp).days if last_event.event_timestamp else 999

        events_30d = len([e for e in events if e.event_timestamp and e.event_timestamp >= thirty_days_ago])

        # Lifetime value from purchases
        lifetime_value = 0.0
        purchase_product_ids = []
        for ev in purchase_events:
            if ev.product_id:
                purchase_product_ids.append(ev.product_id)

        if purchase_product_ids:
            prod_result = await self.db.execute(
                select(Product).where(Product.product_id.in_(purchase_product_ids))
            )
            products = prod_result.scalars().all()
            lifetime_value = sum(p.price for p in products)

        # Average price purchased
        avg_price = 0.0
        if purchase_product_ids:
            prod_result = await self.db.execute(
                select(Product).where(Product.product_id.in_(purchase_product_ids))
            )
            products = prod_result.scalars().all()
            prices = [p.price for p in products if p.price]
            avg_price = sum(prices) / len(prices) if prices else 0.0

        # Brand loyalty
        top_brand_pct = 0.0
        if purchase_product_ids:
            prod_result = await self.db.execute(
                select(Product).where(Product.product_id.in_(purchase_product_ids))
            )
            products = prod_result.scalars().all()
            brand_counts = {}
            for p in products:
                if p.brand:
                    brand_counts[p.brand] = brand_counts.get(p.brand, 0) + 1
            if brand_counts:
                top_brand_count = max(brand_counts.values())
                top_brand_pct = top_brand_count / len(purchase_product_ids)

        return {
            "total_views": len(view_events),
            "purchase_count": len(purchase_events),
            "purchase_events": len(purchase_events),
            "cart_events": len(cart_events),
            "lifetime_value": lifetime_value,
            "avg_price_purchased": avg_price,
            "days_since_first_event": abs(days_since_first),
            "days_since_last_activity": abs(days_since_last),
            "events_30d": events_30d,
            "top_brand_pct": top_brand_pct,
        }

    async def seed_offers(self) -> None:
        """Create predefined offers in the database if they don't exist."""
        now = utcnow()

        # Check if offers already exist
        result = await self.db.execute(select(Offer).limit(1))
        if result.scalar_one_or_none() is not None:
            logger.info("Offers already seeded.")
            return

        for offer_data in PREDEFINED_OFFERS:
            valid_days = offer_data["valid_days"]
            offer = Offer(
                offer_id=str(uuid.uuid4()),
                title=offer_data["title"],
                description=offer_data["description"],
                discount_type=offer_data["discount_type"],
                discount_value=offer_data["discount_value"],
                segment=offer_data["segment"],
                min_purchase=offer_data.get("min_purchase", 0),
                valid_from=now,
                valid_until=now + timedelta(days=valid_days),
                is_active=True,
            )
            self.db.add(offer)

        logger.info(f"Seeded {len(PREDEFINED_OFFERS)} offers.")

    async def assign_offers(self) -> int:
        """
        For each active offer, find matching customers by segment and
        assign the offer. Clears old assignments first.
        Returns number of assignments made.
        """
        now = utcnow()

        # Clear old assignments
        await self.db.execute(delete(CustomerOffer))

        # Get all active offers
        result = await self.db.execute(
            select(Offer).where(
                Offer.is_active == True,
                Offer.valid_from <= now,
                Offer.valid_until >= now,
            )
        )
        offers = result.scalars().all()

        assignments = 0
        for offer in offers:
            # Find customers in this segment
            result = await self.db.execute(
                select(CustomerSegment.customer_id).where(
                    CustomerSegment.segment == offer.segment
                )
            )
            customer_ids = [row[0] for row in result.fetchall()]

            for customer_id in customer_ids:
                self.db.add(CustomerOffer(
                    customer_id=customer_id,
                    offer_id=offer.offer_id,
                    assigned_at=now,
                ))
                assignments += 1

        logger.info(f"Assigned {assignments} offers to customers.")
        return assignments

    async def get_offers_for_customer(self, customer_id: str) -> list[Offer]:
        """Get active offers assigned to a specific customer."""
        now = utcnow()
        result = await self.db.execute(
            select(Offer)
            .join(CustomerOffer, CustomerOffer.offer_id == Offer.offer_id)
            .where(
                CustomerOffer.customer_id == customer_id,
                Offer.is_active == True,
                Offer.valid_from <= now,
                Offer.valid_until >= now,
            )
            .order_by(Offer.valid_until.asc())
        )
        return list(result.scalars().all())

    async def seed_segments(self, customer_id: str) -> None:
        """Assign initial segments for a customer (used during seed data creation)."""
        await self.assign_segments(customer_id)
