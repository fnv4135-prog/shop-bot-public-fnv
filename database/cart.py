"""
database/cart.py - Функции для работы с корзиной
"""

from .connection import get_pool
from .users import ensure_user
import logging

logger = logging.getLogger(__name__)


async def add_to_cart(telegram_id: int, product_id: int, quantity: int = 1) -> bool:
    try:
        logger.info(f"add_to_cart: telegram_id={telegram_id}, product_id={product_id}")
        user_id = await ensure_user(telegram_id)
        logger.info(f"add_to_cart: user_id={user_id}")
        if not user_id:
            logger.error("user_id is None")
            return False

        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO cart_items (user_id, product_id, quantity) 
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, product_id) 
                DO UPDATE SET quantity = cart_items.quantity + EXCLUDED.quantity
            """, user_id, product_id, quantity)

            logger.info(f"add_to_cart: запрос выполнен, товар добавлен")
            logger.info(f"🛒 Товар {product_id} добавлен в корзину пользователя {telegram_id} (user_id={user_id})")
            return True

    except Exception as e:
        logger.error(f"❌ Ошибка добавления в корзину: {e}")
        return False


async def get_cart_items(telegram_id: int):
    try:
        logger.info(f"get_cart_items: telegram_id={telegram_id}")
        user_id = await ensure_user(telegram_id)
        logger.info(f"get_cart_items: user_id={user_id}")
        if not user_id:
            return []
        pool = await get_pool()
        async with pool.acquire() as conn:
            items = await conn.fetch("""
                    SELECT p.id, p.name, p.price, ci.quantity
                    FROM cart_items ci
                    JOIN products p ON ci.product_id = p.id
                    WHERE ci.user_id = $1
                """, user_id)
            logger.info(f"get_cart_items: найдено {len(items)} товаров")
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


async def update_cart_item_quantity(telegram_id: int, product_id: int, new_quantity: int) -> bool:
    """Обновить количество конкретного товара в корзине (если new_quantity <= 0 — удаляем)"""
    if new_quantity <= 0:
        return await remove_from_cart(telegram_id, product_id)

    user_id = await ensure_user(telegram_id)
    if not user_id:
        return False

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Проверяем, есть ли такой товар в корзине
        existing = await conn.fetchval(
            'SELECT quantity FROM cart_items WHERE user_id = $1 AND product_id = $2',
            user_id, product_id
        )
        if existing is None:
            return False

        await conn.execute(
            'UPDATE cart_items SET quantity = $1 WHERE user_id = $2 AND product_id = $3',
            new_quantity, user_id, product_id
        )
        logger.info(f"🔄 Количество товара {product_id} обновлено на {new_quantity} для пользователя {telegram_id}")
        return True


async def remove_from_cart(telegram_id: int, product_id: int) -> bool:
    """Удалить товар из корзины"""
    user_id = await ensure_user(telegram_id)
    if not user_id:
        return False

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            'DELETE FROM cart_items WHERE user_id = $1 AND product_id = $2',
            user_id, product_id
        )
        logger.info(f"🗑 Товар {product_id} удалён из корзины пользователя {telegram_id}")
        return True


async def count_carts():
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(DISTINCT user_id) FROM cart_items"
        )
        return count or 0