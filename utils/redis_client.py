import os
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

_redis_client = None

async def get_redis():
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            logger.warning("REDIS_URL не задан, кэширование отключено")
            return None
        logger.info("🔄 Подключение к Redis...")
        _redis_client = await redis.from_url(redis_url, decode_responses=True)
        logger.info("✅ Подключение к Redis установлено")
    return _redis_client

async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("📴 Подключение к Redis закрыто")

async def clear_cache_pattern(pattern: str):
    redis = await get_redis()
    if redis:
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            logger.info(f"Очищено {len(keys)} ключей по шаблону {pattern}")