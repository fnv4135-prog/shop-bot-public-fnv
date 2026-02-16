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


async def get_all_categories_flat(include_inactive: bool = False):
    """
    Возвращает все категории в виде плоского списка (без построения пути)
    для отображения в выпадающих списках.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT id, name, parent_id, sort_order, is_active
            FROM categories
            WHERE ($1::bool OR is_active)
            ORDER BY sort_order, name
        ''', include_inactive)
        # Добавляем поле path, равное name (для совместимости с шаблоном)
        result = []
        for row in rows:
            d = dict(row)
            d['path'] = d['name']  # временно
            result.append(d)
        return result


async def has_products(category_id: int) -> bool:
    """Проверяет, есть ли товары в данной категории"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            'SELECT COUNT(*) FROM products WHERE category_id = $1',
            category_id
        )
        return count > 0


async def has_subcategories(category_id: int) -> bool:
    """Проверяет, есть ли подкатегории у данной категории"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            'SELECT COUNT(*) FROM categories WHERE parent_id = $1',
            category_id
        )
        return count > 0


async def create_category(name: str, parent_id: int = None, sort_order: int = 0, is_active: bool = True) -> int:
    """Создаёт новую категорию и возвращает её ID"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'INSERT INTO categories (name, parent_id, sort_order, is_active) VALUES ($1, $2, $3, $4) RETURNING id',
            name, parent_id, sort_order, is_active
        )
        logger.info(f"📁 Создана категория '{name}' (id={row['id']})")
        return row['id']


async def update_category(category_id: int, **kwargs):
    """Обновляет поля категории. Допустимые ключи: name, parent_id, sort_order, is_active"""
    allowed = {'name', 'parent_id', 'sort_order', 'is_active'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    set_clause = ', '.join(f"{k} = ${i+1}" for i, k in enumerate(updates))
    values = list(updates.values()) + [category_id]
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            f'UPDATE categories SET {set_clause}, updated_at = NOW() WHERE id = ${len(values)}',
            *values
        )
        logger.info(f"📁 Обновлена категория id={category_id}")
        return True


async def delete_category(category_id: int) -> bool:
    """Удаляет категорию, если у неё нет товаров и подкатегорий. Возвращает True при успехе."""
    if await has_products(category_id) or await has_subcategories(category_id):
        logger.warning(f"⚠️ Нельзя удалить категорию {category_id}: есть товары или подкатегории")
        return False
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM categories WHERE id = $1', category_id)
        logger.info(f"📁 Удалена категория id={category_id}")
        return True