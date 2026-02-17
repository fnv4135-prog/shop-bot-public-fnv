"""
database/promocodes.py - Функции для работы с промокодами
"""
import logging
from datetime import datetime
from database.connection import get_pool

logger = logging.getLogger(__name__)


async def create_promocode(code: str, discount_type: str, discount_value: int,
                           valid_until: str = None, max_uses: int = None) -> int:
    """Создаёт новый промокод, возвращает его ID"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO promocodes (code, discount_type, discount_value, valid_until, max_uses)
            VALUES ($1, $2, $3, $4::date, $5)
            RETURNING id
        ''', code.upper(), discount_type, discount_value, valid_until, max_uses)
        logger.info(f"🎫 Создан промокод {code} (id={row['id']})")
        return row['id']


async def get_promocode(code: str):
    """Возвращает промокод по коду, если он активен и не истёк"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM promocodes
            WHERE code = $1 AND is_active = TRUE
              AND (valid_until IS NULL OR valid_until >= CURRENT_DATE)
              AND (max_uses IS NULL OR used_count < max_uses)
        ''', code.upper())
        return dict(row) if row else None


async def use_promocode(promocode_id: int):
    """Увеличивает счётчик использований промокода"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE promocodes SET used_count = used_count + 1 WHERE id = $1
        ''', promocode_id)


async def get_all_promocodes(include_inactive: bool = False):
    """Возвращает список всех промокодов для админки"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM promocodes
            WHERE ($1::bool OR is_active)
            ORDER BY created_at DESC
        ''', include_inactive)
        return [dict(row) for row in rows]


async def toggle_promocode(promocode_id: int, active: bool):
    """Включает/выключает промокод"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE promocodes SET is_active = $1 WHERE id = $2', active, promocode_id)


async def delete_promocode(promocode_id: int):
    """Удаляет промокод"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM promocodes WHERE id = $1', promocode_id)