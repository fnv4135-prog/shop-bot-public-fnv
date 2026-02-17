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
    """Гарантирует наличие пользователя в таблице users, возвращает его внутренний id"""
    logger.info(f"👤 [ensure_user] Вход: telegram_id={telegram_id}, username={username}, first_name={first_name}, last_name={last_name}")

    if db_conn.pool is None:
        logger.error("❌ [ensure_user] Пул соединений не инициализирован!")
        return None

    async with db_conn.pool.acquire() as conn:
        # Пробуем найти
        row = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )
        if row:
            user_id = row['id']
            logger.info(f"👤 [ensure_user] Пользователь найден: id={user_id}")
            # Обновляем данные
            full = f"{first_name} {last_name}".strip()
            await conn.execute(
                "UPDATE users SET username = COALESCE($2, username), full_name = COALESCE($3, full_name), last_seen = NOW() WHERE id = $1",
                user_id, username, full
            )
            logger.info(f"👤 [ensure_user] Данные пользователя {user_id} обновлены")
            return user_id
        else:
            # Создаём нового
            full = f"{first_name} {last_name}".strip()
            row = await conn.fetchrow(
                "INSERT INTO users (telegram_id, username, full_name) VALUES ($1, $2, $3) RETURNING id",
                telegram_id, username, full
            )
            user_id = row['id']
            logger.info(f"👤 [ensure_user] Создан новый пользователь: telegram_id={telegram_id}, внутренний id={user_id}")
            return user_id


async def get_user_internal_id(telegram_id: int, username: str = "", first_name: str = "", last_name: str = "") -> int:
    """Получить внутренний id пользователя по telegram_id (с созданием при необходимости)"""
    logger.info(f"🔍 [get_user_internal_id] Вызов для telegram_id={telegram_id}")
    result = await ensure_user(telegram_id, username, first_name, last_name)
    logger.info(f"🔍 [get_user_internal_id] Возвращаем id={result}")
    return result

async def get_all_users():
    """Возвращает список всех пользователей (их telegram_id)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT telegram_id FROM users')
        return rows