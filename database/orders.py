import logging
import database.connection as db_conn  # импортируем модуль, а не переменную

logger = logging.getLogger(__name__)


async def create_orders_tables():
    """Создаёт таблицы orders и order_items, если их нет"""
    if db_conn.pool is None:  # обращаемся через модуль
        logger.error("❌ Пул соединений не инициализирован! Таблицы заказов не созданы.")
        return

    async with db_conn.pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_amount INTEGER NOT NULL,
                status VARCHAR(50) DEFAULT 'новый'
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


async def save_order(user_id: int, cart_items: list, total: int) -> int:
    if db_conn.pool is None:
        logger.error("❌ Пул соединений не инициализирован! Заказ не сохранён.")
        return 0

    async with db_conn.pool.acquire() as conn:
        async with conn.transaction():
            order = await conn.fetchrow(
                'INSERT INTO orders (user_id, total_amount) VALUES ($1, $2) RETURNING id',
                user_id, total
            )
            order_id = order['id']
            for item in cart_items:
                await conn.execute('''
                    INSERT INTO order_items (order_id, product_id, product_name, price, quantity)
                    VALUES ($1, $2, $3, $4, $5)
                ''', order_id, item['id'], item['name'], item['price'], item['quantity'])
            return order_id


async def get_user_orders(user_id: int):
    if db_conn.pool is None:
        logger.error("❌ Пул соединений не инициализирован! Заказы не получены.")
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
        ''', user_id)
        return rows