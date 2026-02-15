import logging
import database.connection as db_conn
from database.users import get_user_internal_id

logger = logging.getLogger(__name__)


async def create_orders_tables():
    """Создаёт таблицы orders и order_items, если их нет"""
    if db_conn.pool is None:
        logger.error("❌ Пул соединений не инициализирован! Таблицы заказов не созданы.")
        return

    async with db_conn.pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_amount INTEGER NOT NULL,
                status VARCHAR(50) DEFAULT 'новый',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL,
                product_name VARCHAR(255) NOT NULL,
                price INTEGER NOT NULL,
                quantity INTEGER NOT NULL
            )
        ''')
        logger.info("✅ Таблицы заказов созданы или уже существуют")


async def save_order(telegram_id: int, cart_items: list, total: int, username: str = "", first_name: str = "", last_name: str = "") -> int:
    logger.info(f"📥 save_order вызван: telegram_id={telegram_id}, total={total}, items_count={len(cart_items)}")
    if db_conn.pool is None:
        logger.error("❌ Пул соединений не инициализирован! Заказ не сохранён.")
        return 0

    internal_user_id = await get_user_internal_id(telegram_id, username, first_name, last_name)
    logger.info(f"🆔 internal_user_id={internal_user_id}")
    if not internal_user_id:
        logger.error(f"❌ Не удалось получить внутренний ID для пользователя {telegram_id}")
        return 0

    try:
        async with db_conn.pool.acquire() as conn:
            async with conn.transaction():
                order = await conn.fetchrow(
                    'INSERT INTO orders (user_id, total_amount) VALUES ($1, $2) RETURNING id',
                    internal_user_id, total
                )
                order_id = order['id']
                logger.info(f"✅ Заказ {order_id} вставлен в orders")

                for i, item in enumerate(cart_items):
                    logger.info(f"   ➕ Позиция {i+1}: {item}")
                    await conn.execute('''
                        INSERT INTO order_items (order_id, product_id, product_name, price, quantity)
                        VALUES ($1, $2, $3, $4, $5)
                    ''', order_id, item['id'], item['name'], item['price'], item['quantity'])

                logger.info(f"✅ Заказ {order_id} полностью сохранён")
                return order_id
    except Exception as e:
        logger.exception(f"🔥 Ошибка в save_order: {e}")
        return 0


async def get_user_orders(telegram_id: int):
    if db_conn.pool is None:
        logger.error("❌ Пул соединений не инициализирован! Заказы не получены.")
        return []

    internal_user_id = await get_user_internal_id(telegram_id)
    if not internal_user_id:
        return []

    async with db_conn.pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT o.id, o.order_date, o.total_amount, o.status,
                   json_agg(json_build_object(
                       'product_id', oi.product_id,
                       'product_name', oi.product_name,
                       'price', oi.price,
                       'quantity', oi.quantity
                   )) as items
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.user_id = $1
            GROUP BY o.id
            ORDER BY o.order_date DESC
        ''', internal_user_id)
        return rows


async def get_all_orders_stats():
    """Возвращает общую статистику по всем заказам"""
    if db_conn.pool is None:
        logger.error("❌ Пул соединений не инициализирован! Статистика не получена.")
        return {"total_orders": 0, "total_revenue": 0, "completed_orders": 0, "new_orders": 0}

    async with db_conn.pool.acquire() as conn:
        total = await conn.fetchval('SELECT COUNT(*) FROM orders')
        revenue = await conn.fetchval('SELECT COALESCE(SUM(total_amount), 0) FROM orders')
        completed = await conn.fetchval("SELECT COUNT(*) FROM orders WHERE status = 'выполнен'")
        new = await conn.fetchval("SELECT COUNT(*) FROM orders WHERE status = 'новый'")
        return {
            "total_orders": total,
            "total_revenue": revenue,
            "completed_orders": completed,
            "new_orders": new
        }