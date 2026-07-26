"""Test MCP auth token creation/verification and user lookup type safety."""
import pytest
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, select

from app.mcp.auth import create_access_token, verify_access_token


class _TestBase(DeclarativeBase):
    pass


class _TestUser(_TestBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sub = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_TestBase.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
async def test_access_token_creation_and_verification(db: AsyncSession):
    user = _TestUser(sub="auth0|563", email="test@example.com")
    db.add(user)
    await db.flush()

    token = create_access_token(user.id)
    assert isinstance(token, str) and len(token) > 20

    payload = verify_access_token(token)
    assert payload is not None
    assert payload["user_id"] == user.id


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="SQLite coerces str→int; this bug only manifests in strict DBs like PostgreSQL"
)
async def test_str_conversion_type_mismatch(db: AsyncSession):
    """Demonstrate that str(user_id) breaks Integer column lookup (PostgreSQL behaviour).

    In PostgreSQL, querying an Integer column with a string value returns no rows.
    SQLite is lenient and auto-coerces, masking this bug in dev.
    """
    user = _TestUser(sub="auth0|563", email="test@example.com")
    db.add(user)
    await db.flush()

    token = create_access_token(user.id)
    payload = verify_access_token(token)
    assert payload is not None

    user_id_str = str(payload["user_id"])
    assert isinstance(user_id_str, str)
    assert user_id_str != payload["user_id"]

    result = await db.execute(select(_TestUser).where(_TestUser.id == user_id_str))
    assert result.scalar_one_or_none() is None, (
        "BUG: str(user_id) should NOT match Integer column — "
        "PostgreSQL returns no row; SQLite may coerce but this is unreliable"
    )


@pytest.mark.asyncio
async def test_int_lookup_works_correctly(db: AsyncSession):
    """Direct int query finds the user (the correct approach)."""
    user = _TestUser(sub="auth0|564", email="test2@example.com")
    db.add(user)
    await db.flush()

    token = create_access_token(user.id)
    payload = verify_access_token(token)
    assert payload is not None
    assert isinstance(payload["user_id"], int)

    result = await db.execute(select(_TestUser).where(_TestUser.id == payload["user_id"]))
    found = result.scalar_one_or_none()
    assert found is not None, "Direct int query should find the user"
    assert found.id == user.id
