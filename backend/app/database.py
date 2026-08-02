"""
Async SQLAlchemy engine, session factory, and FastAPI dependency.
Auto-detects SQLite vs Postgres from the DATABASE_URL.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import inspect, text as sa_text
from typing import AsyncGenerator

from app.config import settings


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    # SQLite doesn't need pool sizing; Postgres does
    **({} if _is_sqlite(settings.DATABASE_URL) else {
        "pool_size": 20,
        "max_overflow": 10,
    }),
)

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
        # Lightweight additive migration: add password_hash if missing (existing DBs)
        await _ensure_columns(conn)


async def _ensure_columns(conn) -> None:
    """Add columns that may be missing on pre-existing databases (additive only)."""
    cols = await conn.run_sync(_existing_columns, "customers")
    if cols is not None and "password_hash" not in cols:
        await conn.execute(
            sa_text("ALTER TABLE customers ADD COLUMN password_hash VARCHAR(255)")
        )


def _existing_columns(conn, table: str) -> set[str] | None:
    """Return the existing column names for a table, or None if unavailable."""
    try:
        return {c["name"] for c in inspect(conn).get_columns(table)}
    except Exception:
        return None
