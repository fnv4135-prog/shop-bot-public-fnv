import logging
import database.connection as db_conn

logger = logging.getLogger(__name__)


async def ensure_user(telegram_id: int, username: str = "", first_name: str = "", last_name: str = ""):
    """Гарантирует наличие пользователя в таблице users, возвращает его внутренний id"""
    if db_conn.pool is None:
        logger.error("❌ Пул соединений не инициализирован!")
        return None

    async with db_conn.pool.acquire() as conn:
        # Пробуем найти
        row = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )
        if row:
            user_id = row['id']
            # Обновляем данные
            await conn.execute(
                "UPDATE users SET username = COALESCE($2, username), full_name = COALESCE($3, full_name), last_seen = NOW() WHERE id = $1",
                user_id, username, f"{first_name} {last_name}".strip()
            )
            return user_id
        else:
            # Создаём нового
            row = await conn.fetchrow(
                "INSERT INTO users (telegram_id, username, full_name) VALUES ($1, $2, $3) RETURNING id",
                telegram_id, username, f"{first_name} {last_name}".strip()
            )
            logger.info(f"👤 Создан новый пользователь с telegram_id {telegram_id}, внутренний id {row['id']}")
            return row['id']


async def get_user_internal_id(telegram_id: int, username: str = "", first_name: str = "", last_name: str = ""):
    """Получить внутренний id пользователя по telegram_id (с созданием при необходимости)"""
    return await ensure_user(telegram_id, username, first_name, last_name)