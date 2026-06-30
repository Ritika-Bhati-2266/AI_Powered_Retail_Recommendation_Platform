"""
Seed data generator for the retail hyper-personalisation engine demo.
Generates realistic synthetic customers, products, events, and initial segments.
"""
import uuid
import random
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, Product, Event, CustomerSegment, CustomerOffer
from app.config import settings
from app.utils import utcnow

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

FIRST_NAMES = [
    "Olivia", "Liam", "Emma", "Noah", "Amelia", "Oliver", "Sophia", "Elijah",
    "Isabella", "Mateo", "Mia", "Lucas", "Charlotte", "Levi", "Luna", "Ezra",
    "Harper", "Asher", "Evelyn", "Leo", "Aria", "James", "Ella", "Ethan",
    "Avery", "Benjamin", "Scarlett", "Sebastian", "Grace", "Henry", "Chloe",
    "Muhammad", "Layla", "Jack", "Riley", "Owen", "Zoey", "Daniel", "Nora",
    "Aiden", "Lily", "Samuel", "Eleanor", "Ryan", "Hannah", "Wyatt", "Addison",
    "Carter", "Aubrey", "John", "Ellie", "Luke", "Stella", "Julian", "Natalie",
    "David", "Savannah", "Anthony", "Leah", "Ivan", "Aaliyah", "Nathan", "Skylar",
    "Dylan", "Maya", "Caleb", "Paisley", "Andrew", "Audrey", "Isaac", "Naomi",
    "Thomas", "Kinsley", "Christian", "Aurora", "Gabriel", "Bella", "Theodore",
    "Genesis", "Josiah", "Ariana", "Adrian", "Valentina", "Alex", "Mackenzie",
    "Christopher", "Eva", "Lincoln", "Elena", "Grayson", "Alice", "Ayden", "Sofia",
    "Parker", "Claire", "Cooper", "Sadie", "Santiago", "Caroline",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
    "Patel", "Cruz", "Richards", "Edwards", "Collins", "Chavez", "Stewart",
    "Morris", "Murphy", "Cook", "Rogers", "Morgan", "Peterson", "Cooper",
    "Reed", "Bailey", "Bell", "Gomez", "Kelly", "Howard", "Ward", "Cox",
    "Diaz", "Richardson", "Wood", "Watson", "Brooks", "Bennett", "Gray",
    "James", "Reyes", "Cruz", "Hughes", "Price", "Myers", "Long",
    "Foster", "Sanders", "Ross", "Morales", "Powell", "Sullivan", "Russell",
]

CATEGORIES = {
    "Electronics": ["Smartphones", "Laptops", "Headphones", "Tablets", "Smartwatches", "Cameras"],
    "Clothing": ["T-Shirts", "Jeans", "Dresses", "Jackets", "Shoes", "Accessories"],
    "Home & Kitchen": ["Cookware", "Furniture", "Decor", "Appliances", "Bedding", "Lighting"],
    "Books": ["Fiction", "Non-Fiction", "Science", "History", "Self-Help", "Children"],
    "Sports": ["Fitness", "Outdoor", "Team Sports", "Yoga", "Cycling", "Swimming"],
    "Beauty": ["Skincare", "Makeup", "Haircare", "Fragrance", "Bath & Body", "Tools"],
    "Toys": ["Educational", "Action Figures", "Board Games", "Building Sets", "Dolls", "Puzzles"],
    "Grocery": ["Snacks", "Beverages", "Pantry", "Organic", "International", "Fresh"],
}

BRANDS_BY_CATEGORY = {
    "Electronics": ["TechPro", "ElectroMax", "DigiLife", "SmartWave", "NovaTech", "FusionX"],
    "Clothing": ["FashionFirst", "UrbanStyle", "ClassicWear", "TrendyFit", "LuxeThreads", "VibeApparel"],
    "Home & Kitchen": ["HomeSweet", "KitchenPro", "LivingWell", "ComfortHome", "EliteLiving", "CozyNest"],
    "Books": ["PageTurner", "ReadWise", "BookHaven", "LitWorld", "NovelNest", "BrainFuel"],
    "Sports": ["FitLife", "SportMax", "ActiveGear", "EndurancePro", "PeakPerformance", "IronWill"],
    "Beauty": ["GlowUp", "PureBeauty", "RadianceCo", "NaturalGlow", "LuxeLook", "FreshFace"],
    "Toys": ["FunFactory", "PlayWorld", "ToyChest", "KidJoy", "ImagiNation", "HappyPlay"],
    "Grocery": ["FreshFarm", "NatureBest", "DailyGoods", "PureHarvest", "GreenChoice", "SmartShop"],
}

EVENT_TYPES = ["page_view", "purchase", "add_to_cart", "remove_from_cart", "email_open", "email_click", "wishlist_add"]

# Weights for event type distribution
EVENT_WEIGHTS = {
    "page_view": 0.50,
    "purchase": 0.10,
    "add_to_cart": 0.10,
    "remove_from_cart": 0.05,
    "email_open": 0.03,
    "email_click": 0.02,
    "wishlist_add": 0.05,
}

SEGMENTS = ["high_value", "bargain_hunter", "new_user", "lapsed", "cart_abandoner", "brand_loyalist", "window_shopper", "power_user"]


def random_name() -> tuple[str, str]:
    """Generate a realistic full name."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return first, last


def generate_email(first: str, last: str, idx: int) -> str:
    """Generate a realistic email address with index suffix for uniqueness."""
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com", "icloud.com", "aol.com"]
    patterns = [
        f"{first.lower()}.{last.lower()}",
        f"{first.lower()}{last.lower()}",
        f"{first[0].lower()}{last.lower()}",
        f"{first.lower()}_{last.lower()}",
        f"{last.lower()}{first[0].lower()}",
    ]
    local = random.choice(patterns)
    # Append index to guarantee uniqueness
    return f"{local}{idx}@{random.choice(domains)}"


def get_product_image_url(product_id: str, category: str, idx: int) -> str:
    """Generate a stable product image URL using picsum.photos with a fixed seed.
    Using the product index as a seed ensures the same product always gets the same image."""
    seed = f"product{idx}"
    return f"https://picsum.photos/seed/{seed}/400/300"


def generate_product(product_id: str, category: str, subcategory: str, brand: str, idx: int) -> dict:
    """Generate a realistic product."""
    price_ranges = {
        "Electronics": (15, 2000),
        "Clothing": (10, 300),
        "Home & Kitchen": (5, 800),
        "Books": (5, 80),
        "Sports": (10, 500),
        "Beauty": (3, 150),
        "Toys": (5, 200),
        "Grocery": (1, 50),
    }
    min_price, max_price = price_ranges.get(category, (10, 100))
    price = round(random.uniform(min_price, max_price), 2)

    product_name = f"{brand} {subcategory} {['Pro', 'Elite', 'Classic', 'Premium', 'Essential', 'Deluxe', 'Basic', 'Plus'][idx % 8]}"

    return {
        "product_id": product_id,
        "name": product_name,
        "category": category,
        "subcategory": subcategory,
        "brand": brand,
        "price": price,
        "image_url": get_product_image_url(product_id, category, idx),
    }


def generate_event_time(base_date: datetime, day_offset: int) -> datetime:
    """Generate a realistic event timestamp with hour-of-day bias."""
    # Business hours: 8am-11pm, peak at 10am-2pm and 6pm-9pm
    hour_weights = [0] * 24
    for h in range(8, 23):
        if 10 <= h <= 14:
            hour_weights[h] = 15
        elif 18 <= h <= 21:
            hour_weights[h] = 12
        else:
            hour_weights[h] = 5

    # Weekend vs weekday: slightly more activity on weekends
    event_date = base_date + timedelta(days=day_offset)
    is_weekend = event_date.weekday() >= 5
    multiplier = 1.3 if is_weekend else 1.0

    hour = random.choices(range(24), weights=hour_weights, k=1)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return event_date.replace(hour=hour, minute=minute, second=second, microsecond=0)


def get_segments_for_customer(metrics: dict) -> list[str]:
    """Determine which segments a customer belongs to based on their metrics."""
    assigned = []
    if metrics.get("lifetime_value", 0) > 500 and metrics.get("purchases", 0) > 5:
        assigned.append("high_value")
    if metrics.get("avg_price", 999) < 30 and metrics.get("purchases", 0) > 3:
        assigned.append("bargain_hunter")
    if metrics.get("days_since_first", 999) < 30:
        assigned.append("new_user")
    if metrics.get("days_since_last", 0) > 90:
        assigned.append("lapsed")
    if metrics.get("cart_events", 0) > metrics.get("purchases", 0) and metrics.get("cart_events", 0) > 2:
        assigned.append("cart_abandoner")
    if metrics.get("top_brand_pct", 0) > 0.5 and metrics.get("purchases", 0) > 3:
        assigned.append("brand_loyalist")
    if metrics.get("views", 0) > 50 and metrics.get("purchases", 0) == 0:
        assigned.append("window_shopper")
    if metrics.get("events_30d", 0) > 100:
        assigned.append("power_user")
    return assigned


def generate_price_tier(price: float) -> str:
    if price < 30:
        return "budget"
    elif price < 80:
        return "mid"
    elif price < 150:
        return "premium"
    else:
        return "luxury"


# ── Main Seed Function ──────────────────────────────────────────────────────

async def seed_database(db: AsyncSession) -> None:
    """
    Seed the database with synthetic data if it's empty.
    Creates products, customers, events, segments, and offers.
    """
    # Check if data already exists
    result = await db.execute(select(func.count(Event.event_id)))
    count = result.scalar()
    if count and count > 0:
        logger.info(f"Database already has {count} events. Skipping seed.")
        return

    logger.info("Seeding database with synthetic data...")
    base_date = utcnow() - timedelta(days=90)
    now = utcnow()

    # ── Generate Products ──
    products = []
    product_idx = 0
    for category, subcategories in CATEGORIES.items():
        brands = BRANDS_BY_CATEGORY[category]
        for subcategory in subcategories:
            brand = random.choice(brands)
            # 1-3 products per subcategory
            for _ in range(random.randint(1, 3)):
                product_id = str(uuid.uuid4())
                product_data = generate_product(product_id, category, subcategory, brand, product_idx)
                products.append(product_data)
                product_idx += 1

    # Ensure we have enough products (at least 100 as specified)
    while len(products) < 100:
        category = random.choice(list(CATEGORIES.keys()))
        subcategory = random.choice(CATEGORIES[category])
        brand = random.choice(BRANDS_BY_CATEGORY[category])
        product_id = str(uuid.uuid4())
        product_data = generate_product(product_id, category, subcategory, brand, len(products))
        products.append(product_data)

    # Insert products
    product_objects = {}
    for p in products:
        obj = Product(**p)
        db.add(obj)
        product_objects[p["product_id"]] = obj

    # Flush to get IDs
    await db.flush()

    logger.info(f"Generated {len(products)} products.")

    # ── Generate Customers ──
    customers = []
    customer_count = settings.CUSTOMER_COUNT

    for i in range(customer_count):
        customer_id = str(uuid.uuid4())
        first, last = random_name()
        name = f"{first} {last}"
        email = generate_email(first, last, i)
        # 50% consent rate
        consent_given = random.random() < 0.5

        customer = Customer(
            customer_id=customer_id,
            name=name,
            email=email,
            consent_given=consent_given,
            consent_timestamp=now if consent_given else None,
            created_at=base_date + timedelta(days=random.randint(0, 60)),
        )
        db.add(customer)
        customers.append(customer)

    await db.flush()
    logger.info(f"Generated {customer_count} customers.")

    # ── Generate Events ──
    event_count = settings.EVENT_COUNT
    events_data = []

    # Assign activity levels (pareto-style: 20% of customers generate 80% of events)
    activity_weights = []
    for i in range(customer_count):
        # Some customers are power users, most are casual
        base_weight = random.expovariate(0.5) + 0.1
        activity_weights.append(base_weight)

    total_weight = sum(activity_weights)
    event_assignments = [max(1, int(event_count * w / total_weight)) for w in activity_weights]

    # Adjust to exactly match event_count
    diff = event_count - sum(event_assignments)
    for i in range(abs(diff)):
        event_assignments[i % customer_count] += 1 if diff > 0 else -1

    customer_product_affinities = {}  # customer_id -> list of product_id (preferred products)
    customer_purchase_history = {}  # customer_id -> list of product_id (purchased products)

    for cust_idx, customer in enumerate(customers):
        customer_id = customer.customer_id
        num_events = event_assignments[cust_idx]

        # Pick a preferred category for this customer
        preferred_categories = random.choices(list(CATEGORIES.keys()), k=random.randint(1, 3))
        # Get products in preferred categories
        preferred_products = [p for p in products if p["category"] in preferred_categories]

        purchased_products = []
        viewed_products = set()

        for ev_idx in range(num_events):
            # Determine event type based on weights
            event_type = random.choices(
                list(EVENT_WEIGHTS.keys()),
                weights=list(EVENT_WEIGHTS.values()),
                k=1
            )[0]

            # Pick a product (biased toward preferred categories)
            if preferred_products and random.random() < 0.7:
                product = random.choice(preferred_products)
            else:
                product = random.choice(products)

            product_id = product["product_id"]

            # Day offset: skewed toward recent days with some spread across 90 days
            if event_type == "purchase":
                # Purchases more recent
                day_offset = random.randint(0, 60)
            else:
                day_offset = random.randint(0, 89)

            event_time = generate_event_time(base_date, day_offset)

            metadata = None
            if event_type == "page_view":
                metadata = {"scroll_depth": random.randint(10, 100), "time_on_page": random.randint(5, 300)}
                viewed_products.add(product_id)
            elif event_type == "purchase":
                metadata = {"quantity": random.randint(1, 5), "total_price": product["price"] * random.randint(1, 5)}
                purchased_products.append(product_id)
            elif event_type in ("add_to_cart", "remove_from_cart"):
                metadata = {"quantity": random.randint(1, 3)}
            elif event_type in ("email_open", "email_click"):
                metadata = {"campaign": random.choice(["newsletter", "promo", "abandoned_cart", "welcome"])}
            elif event_type == "wishlist_add":
                metadata = {"note": random.choice(["", "gift idea", "birthday wishlist"])}

            events_data.append({
                "event_id": str(uuid.uuid4()),
                "customer_id": customer_id,
                "product_id": product_id,
                "event_type": event_type,
                "session_id": str(uuid.uuid4()) if random.random() < 0.3 else None,
                "metadata": metadata,
                "event_timestamp": event_time,
            })

        customer_product_affinities[customer_id] = list(viewed_products)
        customer_purchase_history[customer_id] = purchased_products

    # Insert events in batches
    batch_size = 500
    for i in range(0, len(events_data), batch_size):
        batch = events_data[i:i+batch_size]
        for ev_data in batch:
            event = Event(**ev_data)
            db.add(event)
        await db.flush()

    logger.info(f"Generated {len(events_data)} events.")

    # ── Compute metrics and assign segments ──
    from app.offers import OfferEngine
    offer_engine = OfferEngine(db)

    segment_assignments = 0
    for customer in customers:
        metrics = await offer_engine._compute_metrics(customer.customer_id)

        # Add derived metrics for segment evaluation
        metrics["purchases"] = len(customer_purchase_history.get(customer.customer_id, []))
        metrics["views"] = len(customer_product_affinities.get(customer.customer_id, []))

        # Calculate top brand percentage
        purchase_pids = customer_purchase_history.get(customer.customer_id, [])
        if purchase_pids:
            brand_counts = {}
            for pid in purchase_pids:
                p = next((pr for pr in products if pr["product_id"] == pid), None)
                if p and p.get("brand"):
                    brand_counts[p["brand"]] = brand_counts.get(p["brand"], 0) + 1
            if brand_counts:
                metrics["top_brand_pct"] = max(brand_counts.values()) / len(purchase_pids)

        segments = get_segments_for_customer(metrics)
        now = utcnow()
        for segment in segments:
            db.add(CustomerSegment(
                customer_id=customer.customer_id,
                segment=segment,
                assigned_at=now,
            ))
            segment_assignments += 1

    logger.info(f"Assigned {segment_assignments} segments across customers.")

    # ── Seed offers ──
    await offer_engine.seed_offers()
    await offer_engine.assign_offers()

    logger.info("Database seeding complete!")
