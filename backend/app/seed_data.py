"""
Seed data generator for the retail hyper-personalisation engine demo.
Generates realistic synthetic customers, products, events, and initial segments.
"""
import uuid
import random
import hashlib
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

# ── Category-relevant product image pools ──────────────────────────────
# Each category has a pool of verified Unsplash photo IDs that visually
# represent that category (gadgets for Electronics, fitness for Sports, etc.)
# Images are 400x300 crop via Unsplash CDN. A stable hash of the product_id
# deterministically selects which image from the pool a product gets.
CATEGORY_IMAGE_POOL = {
    "Electronics": [
        "photo-1519389950473-47ba0277781c",
        "photo-1498050108023-c5249f4df085",
        "photo-1505740420928-5e560c06d30e",
        "photo-1523275335684-37898b6baf30",
        "photo-1767792828755-2e8fb79f048d",
        "photo-1776107477726-96bacb852f7b",
        "photo-1772182092777-6b1bf0a362fe",
        "photo-1771189958069-a6b00817825c",
        "photo-1778633862334-b5a451746f7a",
        "photo-1502920514313-52581002a659",
        "photo-1517694712202-14dd9538aa97",
        "photo-1504639725590-34d0984388bd",
        "photo-1451187580459-43490279c0fa",
        "photo-1531297484001-80022131f5a1",
        "photo-1555066931-4365d14bab8c",
        "photo-1558618666-fcd25c85f82e",
        "photo-1546868871-af0de0ae72f5",
        "photo-1562401086-265b4710c32f",
        "photo-1493119508027-2b58406e1d60",
        "photo-1526401485004-4695e7a1e8b1",
    ],
    "Clothing": [
        "photo-1523381210434-271e8be1f52b",
        "photo-1490481651871-ab68de25d43d",
        "photo-1460353581641-37baddab0fa2",
        "photo-1556905055-8f358a7a47b2",
        "photo-1568252542512-9fe8fe9c87bb",
        "photo-1593030761757-71fae45fa0e7",
        "photo-1576566588028-4147f3842f27",
        "photo-1492707892479-7bc8d5a4ee93",
        "photo-1485968579580-b6d095142e6e",
        "photo-1507413245164-6160d8298b31",
        "photo-1525507119028-ed4c629a60a3",
        "photo-1529139574466-a303027c1d8b",
        "photo-1496345875659-11f7dd282d1d",
        "photo-1509631179647-0177331693ae",
        "photo-1484154218962-a197022b5858",
        "photo-1513694203232-719a280e022f",
        "photo-1493809842364-78817add7ffb",
        "photo-1505692952047-1a78307da8f2",
        "photo-1512917774080-9991f1c4c750",
        "photo-1560448204-e02f11c3d0e2",
    ],
    "Home & Kitchen": [
        "photo-1556909114-f6e7ad7d3136",
        "photo-1507003211169-0a1dd7228f2d",
        "photo-1556909172-54557c7e4fb7",
        "photo-1484101403633-562f891dc89a",
        "photo-1493663284031-b7e3aefcae8e",
        "photo-1540189549336-e6e99c3679fe",
        "photo-1555041469-a586c61ea9bc",
        "photo-1776935359460-6c789e972e6a",
        "photo-1772567733000-5d5acb9ef4f9",
        "photo-1779457524854-208563209eea",
        "photo-1774716925788-5c4fc543d688",
        "photo-1768525913192-9f5d0d01ec09",
        "photo-1484154218962-a197022b5858",
        "photo-1513694203232-719a280e022f",
        "photo-1493809842364-78817add7ffb",
        "photo-1505692952047-1a78307da8f2",
        "photo-1482049016688-2d3e1b3115e6",
        "photo-1512917774080-9991f1c4c750",
        "photo-1560448204-e02f11c3d0e2",
        "photo-1524758631624-e2822e304c36",
    ],
    "Books": [
        "photo-1512820790803-83ca734da794",
        "photo-1524995997946-a1c2e315a42f",
        "photo-1507842217343-583bb7270b66",
        "photo-1456513080510-7bf3a84b82f8",
        "photo-1768674642533-ad507933232d",
        "photo-1770027705639-25da87b15d35",
        "photo-1481627834876-b7833e8f5570",
        "photo-1491841573634-28140fc7ced7",
        "photo-1532012197267-da84d127e765",
        "photo-1506880018603-83d5b814b5a6",
        "photo-1512070679279-8988d32161be",
        "photo-1521737604893-d14cc237f11d",
        "photo-1432821596592-e2c18b78144f",
        "photo-1516979187457-637abb4f9353",
        "photo-1507413245164-6160d8298b31",
        "photo-1525507119028-ed4c629a60a3",
        "photo-1529139574466-a303027c1d8b",
        "photo-1496345875659-11f7dd282d1d",
        "photo-1509631179647-0177331693ae",
        "photo-1505692952047-1a78307da8f2",
    ],
    "Sports": [
        "photo-1517838277536-f5f99be501cd",
        "photo-1571902943202-507ec2618e8f",
        "photo-1552674605-db6ffd4facb5",
        "photo-1571019613454-1cb2f99b2d8b",
        "photo-1534438327276-14e5300c3a48",
        "photo-1772475625546-e7cec6698a58",
        "photo-1511988617509-a57c8a288659",
        "photo-1558618666-fcd25c85f82e",
        "photo-1517649763962-0c623066013b",
        "photo-1476480862126-209bfaa8edc8",
        "photo-1517457373958-b7bdd4587205",
        "photo-1541534741688-6078c6bfb5c5",
        "photo-1505692952047-1a78307da8f2",
        "photo-1512917774080-9991f1c4c750",
        "photo-1560448204-e02f11c3d0e2",
        "photo-1524758631624-e2822e304c36",
        "photo-1484154218962-a197022b5858",
        "photo-1513694203232-719a280e022f",
        "photo-1493809842364-78817add7ffb",
        "photo-1482049016688-2d3e1b3115e6",
    ],
    "Beauty": [
        "photo-1487412912498-0447578fcca8",
        "photo-1570172619644-dfd03ed5d881",
        "photo-1556228720-195a672e8a03",
        "photo-1596755389378-c31d21fd1273",
        "photo-1775642548281-fcf81fd6f2a3",
        "photo-1747324831504-5ee9aa8eec59",
        "photo-1748543668699-a8a9398e9161",
        "photo-1768483018807-bd0b9ab86539",
        "photo-1451187580459-43490279c0fa",
        "photo-1531297484001-80022131f5a1",
        "photo-1555066931-4365d14bab8c",
        "photo-1558618666-fcd25c85f82e",
        "photo-1504639725590-34d0984388bd",
        "photo-1517694712202-14dd9538aa97",
        "photo-1502920514313-52581002a659",
        "photo-1484154218962-a197022b5858",
        "photo-1513694203232-719a280e022f",
        "photo-1493809842364-78817add7ffb",
        "photo-1505692952047-1a78307da8f2",
        "photo-1512917774080-9991f1c4c750",
    ],
    "Toys": [
        "photo-1596464716127-f2a82984de30",
        "photo-1519331379826-f10be5486c6f",
        "photo-1593085512500-5d55148d6f0d",
        "photo-1587654780291-39c9404d746b",
        "photo-1566577134770-3d85bb3a9cc4",
        "photo-1672888435314-e9b3564cfed0",
        "photo-1563941406054-949225931d52",
        "photo-1775410633856-261eeca07660",
        "photo-1757692144573-3d2e00383cc6",
        "photo-1451187580459-43490279c0fa",
        "photo-1531297484001-80022131f5a1",
        "photo-1504639725590-34d0984388bd",
        "photo-1517694712202-14dd9538aa97",
        "photo-1502920514313-52581002a659",
        "photo-1484154218962-a197022b5858",
        "photo-1513694203232-719a280e022f",
        "photo-1493809842364-78817add7ffb",
        "photo-1505692952047-1a78307da8f2",
        "photo-1512917774080-9991f1c4c750",
        "photo-1560448204-e02f11c3d0e2",
    ],
    "Grocery": [
        "photo-1488459716781-31db52582fe9",
        "photo-1504674900247-0877df9cc836",
        "photo-1542838132-92c53300491e",
        "photo-1769499311767-bce1cf9b4549",
        "photo-1767364084218-a18f3ea7e93f",
        "photo-1774977864908-c730d46b4ec5",
        "photo-1765100213678-5cb8dfb91e41",
        "photo-1771019992524-9d83e1bf69bb",
        "photo-1724333771915-462f370a096d",
        "photo-1685930117878-4b6e76e1de42",
        "photo-1714224247661-ee250f55a842",
        "photo-1451187580459-43490279c0fa",
        "photo-1531297484001-80022131f5a1",
        "photo-1504639725590-34d0984388bd",
        "photo-1517694712202-14dd9538aa97",
        "photo-1502920514313-52581002a659",
        "photo-1484154218962-a197022b5858",
        "photo-1513694203232-719a280e022f",
        "photo-1493809842364-78817add7ffb",
        "photo-1505692952047-1a78307da8f2",
    ],
}


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


def get_product_image_url(product_id: str, category: str) -> str:
    """Return a category-relevant image URL using a stable pool of Unsplash photos.
    Uses a deterministic hash of the product_id so the same product always gets
    the same image from its category's image pool."""
    pool = CATEGORY_IMAGE_POOL.get(category, CATEGORY_IMAGE_POOL.get("Electronics", []))
    # Stable index from product_id hash (deterministic across Python sessions)
    idx = int(hashlib.sha256(product_id.encode()).hexdigest(), 16) % len(pool)
    return f"https://images.unsplash.com/{pool[idx]}?w=400&h=300&fit=crop"


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
        "image_url": get_product_image_url(product_id, category),
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
