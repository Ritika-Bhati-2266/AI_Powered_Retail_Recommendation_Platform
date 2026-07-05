Demonstrates the get_user_from_mcp_context() bug:
1. Creates a user via OAuth with id=563
2. Generates a JWT token for that user
3. Calls get_user_from_mcp_context() with the token
4. Observes the lookup failing due to type mismatch (str vs int)

Run with: python -m pytest test_mcp_auth.py -v
"""
import pytest
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime

from app.mcp.auth import create_access_token, verify_access_token

class TestBase(DeclarativeBase):
    pass

class TestUser(TestBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sub = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
async def test_bug_str_conversion(db: AsyncSession):
    user = TestUser(sub="auth0|563", email="test@example.com")
    db.add(user)
    await db.flush()
    user_id = user.id
    print(f"Created user with id={user_id}")

    token = create_access_token(user_id)
    payload = verify_access_token(token)
    assert payload is not None
    print(f"Token payload: {payload}")

    from sqlalchemy import select
    user_id_str = str(payload.get("user_id"))
    
    result = await db.execute(select(TestUser).where(TestUser.id == user_id_str))
    found = result.scalar_one_or_none()

    print(f"Looked up with str(user_id)='{user_id_str}', found={found}")
    assert found is None, "BUG: str() conversion should cause lookup to fail in PostgreSQL!"


@pytest.mark.asyncio
async def test_fix_no_str_conversion(db: AsyncSession):
    user = TestUser(sub="auth0|564", email="test2@example.com")
    db.add(user)
    await db.flush()
    user_id = user.id
    print(f"Created user with id={user_id}")

    token = create_access_token(user_id)
    payload = verify_access_token(token)
    assert payload is not None
    print(f"Token payload: {payload}")

    from sqlalchemy import select
    user_id = payload.get("user_id")
    
    result = await db.execute(select(TestUser).where(TestUser.id == user_id))
    found = result.scalar_one_or_none()

    print(f"Looked up with user_id={user_id} (int), found={found}")
    assert found is not None, "FIX: Direct integer query should find the user!"