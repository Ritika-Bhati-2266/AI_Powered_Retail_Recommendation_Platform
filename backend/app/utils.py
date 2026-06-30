"""reStructuredText
DB-agnostic utilities for cross-database portability (SQLite dev, Postgres prod).
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current UTC datetime as timezone-naive (portable across SQLite and Postgres)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
