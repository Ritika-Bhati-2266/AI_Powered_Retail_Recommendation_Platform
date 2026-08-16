import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.mcp.auth import create_access_token, oauth_callback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.post("/oauth/callback")
async def oauth_callback_endpoint(
    sub: str,
    email: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    user = await oauth_callback(sub, email, db)
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user_id": user.id,
    }
