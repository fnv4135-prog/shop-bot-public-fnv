import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()


async def check():
    """Быстрая проверка состояния БД"""
    # Правильный путь к корню проекта
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from database import init_pool, get_all_products, get_cart_items

    await init_pool()

    # Проверяем товары
    products = await get_all_products()
    print(f"📦 Товаров в БД: {len(products)}")

    # Проверяем пользователей
    from database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"👤 Пользователей: {users_count}")

        orders_count = await conn.fetchval("SELECT COUNT(*) FROM orders")
        print(f"📝 Заказов: {orders_count}")

    print("✅ Проверка завершена")


if __name__ == "__main__":
    asyncio.run(check())