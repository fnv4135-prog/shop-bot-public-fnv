"""
database/categories.py - Функции для работы с категориями
"""
import logging
from database.connection import get_pool

logger = logging.getLogger(__name__)


async def get_category_tree(parent_id: int = None, include_inactive: bool = False):
    """
    Возвращает дерево категорий начиная с указанного родителя.
    Если parent_id = None, возвращаются корневые категории.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Получаем все категории, которые нужно отобразить
        rows = await conn.fetch('''
            SELECT * FROM categories
            WHERE ($1::bool OR is_active)
              AND (($2::int IS NULL AND parent_id IS NULL) OR parent_id = $2)
            ORDER BY sort_order, name
        ''', include_inactive, parent_id)

        # Если это корневые категории, для каждой подгружаем подкатегории
        if parent_id is None:
            tree = []
            for row in rows:
                cat = dict(row)
                cat['children'] = await get_category_tree(row['id'], include_inactive)
                tree.append(cat)
            return tree
        else:
            # Для не-корневых возвращаем плоский список
            return [dict(row) for row in rows]


async def get_category_children(category_id: int, include_inactive: bool = False):
    """Возвращает прямых потомков категории (без глубокой вложенности)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM categories
            WHERE parent_id = $1 AND ($2::bool OR is_active)
            ORDER BY sort_order, name
        ''', category_id, include_inactive)
        return [dict(row) for row in rows]


async def get_products_by_category(category_id: int, include_inactive: bool = False):
    """Возвращает товары в указанной категории"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT id, name, price, description, is_active
            FROM products
            WHERE category_id = $1 AND ($2::bool OR is_active)
            ORDER BY name
        ''', category_id, include_inactive)
        return [dict(row) for row in rows]


async def get_category_name(category_id: int) -> str:
    """Возвращает название категории по её ID"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchval(
            'SELECT name FROM categories WHERE id = $1',
            category_id
        )
        return row