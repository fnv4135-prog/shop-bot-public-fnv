# utils/cleanup.py
import logging

logger = logging.getLogger(__name__)

async def cleanup_old_sessions(bot_token: str):
    """Очистка старых сессий (заглушка)"""
    logger.info("🧹 Очистка старых сессий...")
    return True