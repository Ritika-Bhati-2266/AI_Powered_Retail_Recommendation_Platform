"""
Authentication and authorisation helpers for the API.

- Password hashing via bcrypt.
- Signed JWT access tokens (HS256) using a secret from the environment.
- FastAPI dependencies that make the bearer token the source of truth for the
  authenticated customer, and that enforce ownership on per-customer routes.

Note: the legacy `X-User-Email` header is no longer trusted for any protected
route; consumers must present a valid `Authorization: Bearer <token>`.
"""
import logging

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Customer


async def __get_authorization_header(authorization: str | None = Header(None)) -> str | None:
    """FastAPI dependency to surface the raw Authorization header value."""
    return authorization

logger = logging.getLogger(__name__)


def hash_password(plain: str, rounds: int = 12) -> str:
    """Hash a plaintext password with a random salt.

    Real user passwords use the default cost (rounds=12). Demo/seed data may
    pass a lower cost (e.g. rounds=10) to keep seeded startup fast.
    """
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(plain: str, hashed: str | None) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(customer_id: str, role: str) -> str:
    """Create a signed JWT access token for a customer."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": customer_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decode and verify a JWT; return its payload or None if invalid/expired."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as e:
        logger.warning("Token verification failed: %s", e)
        return None


def _extract_bearer(credentials: str | None) -> str | None:
    if not credentials:
        return None
    parts = credentials.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    # tolerate a raw token (no scheme)
    if len(parts) == 1 and parts[0]:
        return parts[0]
    return None


async def get_current_customer(
    credentials: str | None = Depends(__get_authorization_header),
    db: AsyncSession = Depends(get_db),
) -> Customer:
    """Resolve the authenticated Customer from the bearer token (source of truth)."""
    token = _extract_bearer(credentials)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    customer_id = payload.get("sub")
    if not customer_id:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    result = await db.execute(select(Customer).where(Customer.customer_id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=401, detail="Account not found")
    return customer


async def require_owner(
    customer_id: str,
    current: Customer = Depends(get_current_customer),
) -> Customer:
    """Dependency: caller must own `customer_id`, or be an admin.

    The resource path parameter is the source of truth for which customer's data
    is being requested; the token must match it (unless the caller is admin).
    """
    if current.role != "admin" and current.customer_id != customer_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: you can only access your own account data.",
        )
    return current