"""
OfferEngine: segment assignment, offer management, and personalised offer delivery.
"""
import logging
import uuid
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.currency import convert_price, price_to_usd
from app.models import (
    Customer,
    CustomerCategoryPreference,
    CustomerOffer,
    CustomerSegment,
    Event,
    Offer,
    Order,
    OrderItem,
    Product,
)
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


# ── Personalised discount bounds (business-safe) ─────────────────────────────

PERSONALISED_DISCOUNT_MIN = 5.0
PERSONALISED_DISCOUNT_MAX = 30.0


def _clamp_discount(value: float) -> float:
    """Clamp a computed discount into the business-safe [min, max] range."""
    return round(max(PERSONALISED_DISCOUNT_MIN, min(PERSONALISED_DISCOUNT_MAX, value)), 1)


class OfferEngine:
    """Manages segment assignment and offer targeting."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def assign_segments(self, customer_id: str) -> list[str]:
        """
        Evaluate a customer against all segment definitions and assign
        matching segments. Returns list of assigned segment names.

        This is the single canonical implementation of segment evaluation —
        seed data, signup and event ingestion all route through here so the
        same rules and metrics always apply.

        Non-consenting customers and admin accounts are never segmented.
        """
        # Guard: only shopper accounts with active consent can be segmented.
        result = await self.db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        )
        customer = result.scalar_one_or_none()
        if customer is None or customer.role != "customer" or not customer.consent_given:
            await self.db.execute(
                delete(CustomerSegment).where(CustomerSegment.customer_id == customer_id)
            )
            return []

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

        # A brand-new shopper with no behaviour events yet is a new user.
        if metrics.get("total_events", 0) == 0:
            assigned_segments.append("new_user")

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

        # Get all events for this customer
        result = await self.db.execute(
            select(Event).where(Event.customer_id == customer_id)
        )
        events = result.scalars().all()

        total_events = len(events)
        if total_events == 0:
            return {
                "total_events": 0,
                "total_views": 0,
                "purchase_count": 0,
                "purchase_events": 0,
                "cart_events": 0,
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

        # Lifetime value — true spend derived from order line-item snapshots
        # (quantity × unit price), matching the value reported by the customer
        # profile endpoint rather than summing catalogue prices. Order line
        # prices are stored in the order's currency, so each line is converted
        # back to USD before summing — otherwise a non-USD customer's LTV would
        # be inflated by the currency multiplier and break every USD-based
        # segment threshold (high_value > 500, bargain_hunter < 30, ...).
        lv_result = await self.db.execute(
            select(Order.currency, OrderItem.quantity, OrderItem.unit_price)
            .select_from(OrderItem)
            .join(Order, Order.order_id == OrderItem.order_id)
            .where(Order.customer_id == customer_id)
        )
        lifetime_value = sum(
            price_to_usd((qty or 0) * (price or 0), order_currency)
            for order_currency, qty, price in lv_result.all()
        )

        purchase_product_ids = [ev.product_id for ev in purchase_events if ev.product_id]

        # Average price purchased (from the products actually purchased)
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
            "total_events": total_events,
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
        """Create or refresh predefined offers with validity relative to now."""
        now = utcnow()

        # Check if offers already exist
        result = await self.db.execute(select(Offer).limit(1))
        existing = result.scalar_one_or_none()

        if existing is not None:
            # Refresh validity dates for existing offers
            result = await self.db.execute(select(Offer))
            all_offers = result.scalars().all()
            for offer in all_offers:
                for offer_data in PREDEFINED_OFFERS:
                    if offer_data["title"] == offer.title:
                        valid_days = offer_data["valid_days"]
                        offer.valid_from = now
                        offer.valid_until = now + timedelta(days=valid_days)
                        offer.is_active = True
                        break
            logger.info(f"Refreshed {len(all_offers)} offers validity.")
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
                Offer.is_active,
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
                Offer.is_active,
                Offer.valid_from <= now,
                Offer.valid_until >= now,
            )
            .order_by(Offer.valid_until.asc())
        )
        return list(result.scalars().all())

    async def get_personalised_offers_for_customer(self, customer_id: str) -> list[dict]:
        """
        Personalised offer delivery: keep the predefined segment-based offer
        structure (titles + descriptions), but compute a customer-specific
        discount percentage and reason from the customer's own behaviour
        metrics. Every returned offer carries a dynamic `discount_percentage`
        clamped to [PERSONALISED_DISCOUNT_MIN, PERSONALISED_DISCOUNT_MAX]
        (5%–30%) plus a short human-readable `reason`.
        """
        offers = await self.get_offers_for_customer(customer_id)
        if not offers:
            return []

        metrics = await self._compute_metrics(customer_id)
        category_prefs = await self._get_category_preferences(customer_id)

        items = []
        for offer in offers:
            discount_pct, reason = self._compute_personalised_discount(
                offer.segment, metrics, category_prefs
            )

            description = offer.description
            if offer.segment == "new_user" and category_prefs:
                description = (
                    f"{offer.description} "
                    f"Targeted at: {', '.join(category_prefs)}."
                )

            # Promote the cart-abandoner "free shipping" placeholder into a real
            # percentage so it scales with the customer's actual abandon ratio.
            if offer.segment in ("cart_abandoner", "bargain_hunter", "high_value",
                                 "lapsed", "brand_loyalist", "window_shopper", "power_user"):
                offer_type = "percentage"
            else:
                offer_type = offer.discount_type

            discount_value = discount_pct if offer_type == "percentage" else offer.discount_value

            items.append({
                "offer_id": offer.offer_id,
                "title": offer.title,
                "description": description,
                "discount_type": offer_type,
                "discount_value": discount_value,
                "discount_percentage": discount_pct,
                "min_purchase": offer.min_purchase,
                "valid_until": offer.valid_until,
                "reason": reason,
            })

        return items

    async def get_checkout_discount(
        self,
        customer_id: str,
        currency: str,
        subtotal: float,
    ) -> dict | None:
        """
        Pick the single best applicable offer for a checkout subtotal.

        Used by the order endpoint so the discount a customer sees on their
        offers panel is the one actually applied at checkout. Returns
        ``None`` when the customer has no assigned offer whose minimum
        purchase threshold is met.

        The returned ``discount_amount`` (and the ``subtotal`` it is compared
        against) are in ``currency`` — min_purchase thresholds are stored in
        USD, so they are converted to ``currency`` before comparison. The best
        offer is the one yielding the largest discount; a no-op (free-shipping
        placeholder) offer is skipped.
        """
        offers = await self.get_personalised_offers_for_customer(customer_id)
        if not offers:
            return None

        best: dict | None = None
        for offer in offers:
            min_purchase_local = convert_price(offer.get("min_purchase", 0) or 0, currency)[0]
            if subtotal < min_purchase_local:
                continue
            if offer["discount_type"] == "percentage":
                pct = offer.get("discount_percentage") or offer.get("discount_value") or 0.0
                discount = round(subtotal * pct / 100.0, 2)
            else:
                # Fixed-amount offers store their value in USD — convert to the
                # order currency so the applied discount matches display.
                discount = round(convert_price(offer.get("discount_value", 0) or 0, currency)[0], 2)
            if discount <= 0:
                continue
            discount = min(discount, subtotal)
            if best is None or discount > best["discount_amount"]:
                best = {
                    "offer_id": offer["offer_id"],
                    "title": offer["title"],
                    "discount_type": offer["discount_type"],
                    "discount_percentage": offer.get("discount_percentage"),
                    "discount_value": offer.get("discount_value"),
                    "min_purchase": offer.get("min_purchase", 0),
                    "discount_amount": discount,
                }
        return best

    async def _get_category_preferences(self, customer_id: str) -> list[str]:
        """Fetch stored category preferences for a customer."""
        result = await self.db.execute(
            select(CustomerCategoryPreference.category)
            .where(CustomerCategoryPreference.customer_id == customer_id)
            .order_by(CustomerCategoryPreference.category)
        )
        return list(result.scalars().all())

    def _compute_personalised_discount(
        self,
        segment: str,
        metrics: dict,
        category_prefs: list[str] | None = None,
    ) -> tuple[float, str]:
        """
        Compute a customer-specific discount percentage (5–30%) and a short
        reason from behavioural metrics. Segment-aware business rules.

        - high_value:      LTV / purchase frequency strong -> slightly LOWER
                           discount (retention already good, protect margin).
        - bargain_hunter:  cheaper average basket -> bigger discount (price-sensitive).
        - cart_abandoner:  higher abandon ratio -> bigger recovery incentive.
        - new_user:        targeted welcome offer on the customer's chosen categories.
        - lapsed:          longer inactivity -> stronger win-back discount.
        - brand_loyalist:  higher brand concentration -> bonus reward.
        - window_shopper:  more browsing -> nudge towards first purchase.
        - power_user:      high 30-day activity -> appreciation reward.
        """
        category_prefs = category_prefs or []
        days_inactive = metrics.get("days_since_last_activity", 0) or 0

        if segment == "high_value":
            ltv = metrics.get("lifetime_value", 0.0) or 0.0
            active_days = metrics.get("days_since_first_event", 1) or 1
            if active_days >= 999:
                active_days = 1
            purchase_frequency = metrics.get("purchase_count", 0) / max(1, active_days / 30.0)
            reduction = (
                5.0 * min(ltv / 10000.0, 1.0)
                + 3.0 * min(purchase_frequency / 2.0, 1.0)
            )
            return _clamp_discount(25.0 - reduction), (
                "Exclusive VIP offer — you're one of our most valuable customers"
            )

        if segment == "bargain_hunter":
            avg_price = metrics.get("avg_price_purchased", 0.0) or 0.0
            price_factor = max(0.0, min((30.0 - avg_price) / 30.0, 1.0))
            return _clamp_discount(20.0 + 8.0 * price_factor), (
                "Tuned to your deal-seeking purchase history"
            )

        if segment == "cart_abandoner":
            cart_events = metrics.get("cart_events", 0) or 0
            purchase_events = metrics.get("purchase_events", 0) or 0
            total = cart_events + purchase_events
            ratio = cart_events / total if total > 0 else 0.5
            return _clamp_discount(15.0 + 8.0 * ratio), (
                "We noticed items left in your cart — finish what you started"
            )

        if segment == "lapsed":
            intensity = min(days_inactive / 90.0, 1.0)
            return _clamp_discount(18.0 + 12.0 * intensity), (
                f"Win-back offer — {days_inactive} days since your last visit"
            )

        if segment == "brand_loyalist":
            pct = max(0.0, min(metrics.get("top_brand_pct", 0.0) or 0.0, 1.0))
            return _clamp_discount(8.0 + 12.0 * pct), (
                "Loyalty reward for your favorite brand"
            )

        if segment == "window_shopper":
            views = metrics.get("total_views", 0) or 0
            return _clamp_discount(10.0 + min(views / 20.0, 5.0)), (
                "We noticed you're browsing — here's a nudge to make your first purchase"
            )

        if segment == "power_user":
            events_30d = metrics.get("events_30d", 0) or 0
            return _clamp_discount(12.0 + min(events_30d / 100.0 * 3.0, 6.0)), (
                "Reward for being one of our most active shoppers"
            )

        # new_user (default) — targeted welcome offer.
        if category_prefs:
            return 15.0, (
                f"Welcome offer on {', '.join(category_prefs)} — categories you said you love"
            )
        return 12.0, "Welcome offer for new customers"

    async def seed_segments(self, customer_id: str) -> None:
        """Assign initial segments for a customer (used during seed data creation)."""
        await self.assign_segments(customer_id)
