"""
Async SQLAlchemy engine, session factory, and FastAPI dependency.
Auto-detects SQLite vs Postgres from the DATABASE_URL.
"""
from collections.abc import AsyncGenerator

from sqlalchemy import inspect
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


# ── Engine construction ──────────────────────────────────────────────────────
# SQLite: use WAL journal mode + a generous busy timeout so the backend can
# keep serving reads while one-off migration/maintenance scripts (ALTER TABLE,
# bulk updates) hold the write lock, instead of failing with "database is
# locked" or stalling requests. Postgres uses a sized pool instead.
_engine_kwargs: dict = {
    "echo": False,
    "pool_pre_ping": True,
}
if _is_sqlite(settings.DATABASE_URL):
    _engine_kwargs["connect_args"] = {"timeout": 30}  # sqlite busy timeout (s)
else:
    _engine_kwargs["pool_size"] = 20
    _engine_kwargs["max_overflow"] = 10

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

if _is_sqlite(settings.DATABASE_URL):
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, connection_record):
        """Per-connection SQLite settings: WAL + long busy timeout."""
        cur = dbapi_conn.cursor()
        try:
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=30000")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("PRAGMA foreign_keys=ON")
        finally:
            cur.close()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables defined in models if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Backfill columns that pre-existing databases may be missing.
        await _ensure_columns(conn)


# Columns that older builds shipped without. ``create_all`` never adds columns
# to an existing table, so without this backfill a legacy database would raise
# "no such column" on every customer INSERT (e.g. signup) and return a raw 500.
# (column_name, sqlite DDL, postgres DDL) — defaults are constant so existing
# rows get a valid value and the NOT NULL constraints stay satisfied.
_ADDITIVE_CUSTOMER_COLUMNS = [
    ("consent_timestamp", "consent_timestamp DATETIME", "consent_timestamp TIMESTAMP"),
    ("role", "role VARCHAR(50) DEFAULT 'customer' NOT NULL", "role VARCHAR(50) DEFAULT 'customer' NOT NULL"),
    ("currency", "currency VARCHAR(3) DEFAULT 'USD' NOT NULL", "currency VARCHAR(3) DEFAULT 'USD' NOT NULL"),
    ("password_hash", "password_hash VARCHAR(255)", "password_hash VARCHAR(255)"),
]


async def _ensure_columns(conn) -> None:
    """Add columns that may be missing on pre-existing databases (additive only)."""
    is_sqlite = _is_sqlite(settings.DATABASE_URL)
    cols = await conn.run_sync(_existing_columns, "customers")
    if cols is None:
        return
    for name, sqlite_ddl, pg_ddl in _ADDITIVE_CUSTOMER_COLUMNS:
        if name in cols:
            continue
        ddl = sqlite_ddl if is_sqlite else pg_ddl
        await conn.execute(sa_text(f"ALTER TABLE customers ADD COLUMN {ddl}"))


def _existing_columns(conn, table: str) -> set[str] | None:
    """Return the existing column names for a table, or None if unavailable."""
    try:
        return {c["name"] for c in inspect(conn).get_columns(table)}
    except Exception:
        return None
