"""
database/cart.py - Функции для работы с корзиной
"""

from .connection import get_pool
from .users import ensure_user
import logging

logger = logging.getLogger(__name__)


async def add_to_cart(telegram_id: int, product_id: int, quantity: int = 1) -> bool:
    try:
        # Получаем внутренний id пользователя
        user_id = await ensure_user(telegram_id)
        if not user_id:
            logger.error(f"❌ Не удалось получить внутренний id для пользователя {telegram_id}")
            return False

        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO cart_items (user_id, product_id, quantity) 
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, product_id) 
                DO UPDATE SET quantity = cart_items.quantity + EXCLUDED.quantity
            """, user_id, product_id, quantity)

            logger.info(f"🛒 Товар {product_id} добавлен в корзину пользователя {telegram_id} (user_id={user_id})")
            return True

    except Exception as e:
        logger.error(f"❌ Ошибка добавления в корзину: {e}")
        return False


async def get_cart_items(telegram_id: int):
    try:
        user_id = await ensure_user(telegram_id)
        if not user_id:
            return []

        pool = await get_pool()
        async with pool.acquire() as conn:
            items = await conn.fetch("""
                SELECT p.id, p.name, p.price, ci.quantity
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                WHERE ci.user_id = $1
                ORDER BY ci.added_at
            """, user_id)

            return [dict(item) for item in items]

    except Exception as e:
        logger.error(f"❌ Ошибка получения корзины: {e}")
        return []


async def clear_cart(telegram_id: int) -> bool:
    try:
        user_id = await ensure_user(telegram_id)
        if not user_id:
            return False

        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM cart_items WHERE user_id = $1",
                user_id
            )

            logger.info(f"🗑 Корзина пользователя {telegram_id} очищена")
            return True

    except Exception as e:
        logger.error(f"❌ Ошибка очистки корзины: {e}")
        return False


async def count_carts():
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(DISTINCT user_id) FROM cart_items"
        )
        return count or 0