import logging
import os
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User

# MCP/helper-auth signing secret. Never hardcode a production secret: use the
# main app's SECRET_KEY (which itself must be set via env in production) or an
# explicit MCP_JWT_SECRET override.
JWT_SECRET = os.environ.get("MCP_JWT_SECRET") or settings.SECRET_KEY
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

logger = logging.getLogger(__name__)


def create_access_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        logger.warning("Token verification failed: %s", e)
        return None


async def oauth_callback(sub: str, email: str | None, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.sub == sub))
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(sub=sub, email=email)
    db.add(user)
    await db.flush()
    logger.info("Created new user via OAuth: id=%s sub=%s", user.id, user.sub)
    return user
