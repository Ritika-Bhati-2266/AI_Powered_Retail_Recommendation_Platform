"""reStructuredText
DB-agnostic utilities for cross-database portability (SQLite dev, Postgres prod).
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current UTC datetime as timezone-naive (portable across SQLite and Postgres)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_price_tier(price: float) -> str:
    """Map a price to a descriptive tier label."""
    if price < 20:
        return "budget"
    if price < 50:
        return "economy"
    if price < 100:
        return "mid"
    if price < 200:
        return "premium"
    return "luxury"
