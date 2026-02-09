"""
database/connection.py - Управление подключением к PostgreSQL
"""

import os
import asyncpg
from typing import Optional
import logging
from dotenv import load_dotenv  # ДОБАВЬТЕ ЭТУ СТРОКУ

# ЗАГРУЖАЕМ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
load_dotenv()  # ДОБАВЬТЕ ЭТУ СТРОКУ

logger = logging.getLogger(__name__)

# Глобальный пул подключений
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Получить пул подключений к БД"""
    global _pool
    if _pool is None:
        await init_pool()
    return _pool


async def init_pool():
    """Инициализация пула подключений"""
    global _pool
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("❌ DATABASE_URL не найден в переменных окружения")
            raise ValueError("DATABASE_URL не найден")

        _pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=1,
            max_size=10,
            command_timeout=60,
            server_settings={'search_path': 'public'}
        )
        logger.info("✅ Пул подключений PostgreSQL создан")

    except Exception as e:
        logger.error(f"❌ Ошибка создания пула подключений: {e}")
        raise


async def close_pool():
    """Закрытие пула подключений"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("✅ Пул подключений закрыт")