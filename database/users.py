"""
database/users.py - Функции для работы с пользователями
"""
import logging
import database.connection as db_conn

logger = logging.getLogger(__name__)


async def create_users_table():
    """Создаёт таблицу users, если её нет"""
    if db_conn.pool is None:
        logger.error("❌ Пул соединений не инициализирован! Таблица users не создана.")
        return

    async with db_conn.pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(100),
                full_name VARCHAR(200),
                created_at TIMESTAMP DEFAULT NOW(),
                last_seen TIMESTAMP DEFAULT NOW()
            )
        ''')
        logger.info("✅ Таблица users создана или уже существует")


async def ensure_user(telegram_id: int, username: str = "", first_name: str = "", last_name: str = "") -> int:
    # ... (оставь без изменений, у тебя он уже есть)
    pass


async def get_user_internal_id(telegram_id: int, username: str = "", first_name: str = "", last_name: str = "") -> int:
    return await ensure_user(telegram_id, username, first_name, last_name)


async def get_all_users():
    """Возвращает список всех пользователей (их telegram_id)"""
    if db_conn.pool is None:
        logger.error("❌ Пул соединений не инициализирован! Не могу получить пользователей.")
        return []
    async with db_conn.pool.acquire() as conn:
        rows = await conn.fetch('SELECT telegram_id FROM users')
        return [dict(row) for row in rows]