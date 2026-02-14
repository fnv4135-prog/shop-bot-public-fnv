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
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("✅ Таблица users создана или уже существует")


async def ensure_user(user_id: int, username: str = "", first_name: str = "", last_name: str = ""):
    """Проверяет наличие пользователя в таблице и добавляет, если отсутствует"""
    if db_conn.pool is None:
        logger.error("❌ Пул соединений не инициализирован! Не могу проверить пользователя.")
        return

    async with db_conn.pool.acquire() as conn:
        # Проверяем, существует ли пользователь
        exists = await conn.fetchval('SELECT 1 FROM users WHERE user_id = $1', user_id)
        if not exists:
            # Вставляем нового пользователя
            await conn.execute('''
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES ($1, $2, $3, $4)
            ''', user_id, username, first_name, last_name)
            logger.info(f"👤 Добавлен новый пользователь {user_id} в таблицу users")