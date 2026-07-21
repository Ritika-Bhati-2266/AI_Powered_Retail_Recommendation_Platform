"""
Redis caching layer for recommendations and product queries.
Gracefully degrades when Redis is not configured.
"""
import json
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_redis = None


async def get_redis():
    global _redis
    if _redis is not None:
        return _redis
    if not settings.REDIS_URL:
        return None
    try:
        from redis.asyncio import Redis
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await _redis.ping()
        logger.info("Connected to Redis at %s", settings.REDIS_URL)
        return _redis
    except Exception as e:
        logger.warning("Redis unavailable, caching disabled: %s", e)
        _redis = False
        return None


async def cache_get(key: str) -> Optional[str]:
    r = await get_redis()
    if r is None:
        return None
    try:
        return await r.get(key)
    except Exception as e:
        logger.warning("Redis get failed: %s", e)
        return None


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    r = await get_redis()
    if r is None:
        return
    try:
        await r.setex(key, ttl, value)
    except Exception as e:
        logger.warning("Redis set failed: %s", e)


async def cache_delete(pattern: str) -> None:
    r = await get_redis()
    if r is None:
        return
    try:
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
    except Exception as e:
        logger.warning("Redis delete failed: %s", e)


async def close_redis() -> None:
    global _redis
    if _redis and _redis is not False:
        await _redis.close()
        _redis = None
