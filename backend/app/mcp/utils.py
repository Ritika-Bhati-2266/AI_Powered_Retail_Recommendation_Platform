import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.auth import verify_access_token
from app.models import User

logger = logging.getLogger(__name__)


async def get_user_from_mcp_context(token: str, db: AsyncSession) -> User | None:
    payload = verify_access_token(token)
    if payload is None:
        logger.warning("Invalid or expired OAuth token")
        return None

    user_id_raw = payload.get("user_id")
    if user_id_raw is None:
        logger.warning("OAuth token missing user_id")
        return None
    user_id = int(user_id_raw)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning(
            "OAuth access token refers to unknown user id user_id=%s",
            payload.get("user_id"),
        )
        return None

    return user
