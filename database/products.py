"""
database/products.py - Функции для работы с товарами
"""

from .connection import get_pool
import logging

logger = logging.getLogger(__name__)


async def get_all_products():
    """Получить все активные товары"""
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, description, price, image_url, category FROM products WHERE is_active = TRUE ORDER BY id"
        )
        return [dict(row) for row in rows]


async def get_product_by_id(product_id: int):
    """Получить товар по ID"""
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, description, price, image_url, category FROM products WHERE id = $1 AND is_active = TRUE",
            product_id
        )
        return dict(row) if row else None


async def get_product_by_id(product_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT id, name, price, description, category_id, is_active
            FROM products
            WHERE id = $1
        ''', product_id)
        return dict(row) if row else None


async def search_products(query: str, limit: int = 20):
    """
    Ищет товары по названию (регистронезависимо, с поддержкой русских символов)
    Возвращает список товаров.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Используем ILIKE для регистронезависимого поиска
        rows = await conn.fetch('''
            SELECT id, name, price, description
            FROM products
            WHERE is_active AND name ILIKE $1
            ORDER BY name
            LIMIT $2
        ''', f'%{query}%', limit)
        return [dict(row) for row in rows]


async def create_product(name: str, description: str, price: int, image_url: str = None):
    """Создать новый товар"""
    pool = await get_pool()

    async with pool.acquire() as conn:
        product_id = await conn.fetchval(
            """
            INSERT INTO products (name, description, price, image_url)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            name, description, price, image_url
        )
        logger.info(f"Создан товар #{product_id}: {name}")
        return product_id


# ========== ДОБАВЛЯЕМ НУЖНЫЕ ФУНКЦИИ ДЛЯ АДМИНКИ ==========

async def add_product(name: str, description: str, price: int, category: str = "Без категории"):
    """Добавить товар в БД (используется в админке)"""
    pool = await get_pool()

    async with pool.acquire() as conn:
        product_id = await conn.fetchval(
            """
            INSERT INTO products (name, description, price, category, is_active)
            VALUES ($1, $2, $3, $4, TRUE)
            RETURNING id
            """,
            name, description, price, category
        )
        logger.info(f"Добавлен товар #{product_id}: {name} за {price}₽")
        return product_id


async def count_products() -> int:
    """Подсчитать количество активных товаров"""
    pool = await get_pool()

    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM products WHERE is_active = TRUE")
        return count


async def migrate_initial_data() -> int:
    """Миграция начальных данных – отключена, чтобы не мешать реальным товарам"""
    return 0