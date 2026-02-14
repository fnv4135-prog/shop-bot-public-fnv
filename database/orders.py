import logging
from database import pool  # общий пул соединений

logger = logging.getLogger(__name__)


async def create_orders_tables():
    """Создаёт таблицы orders и order_items, если их нет"""
    async with pool.acquire() as conn:
        # Таблица заказов
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_amount INTEGER NOT NULL,
                status VARCHAR(50) DEFAULT 'новый'
            )
        ''')

        # Таблица позиций заказа
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
    """Сохраняет заказ в БД и возвращает его ID"""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Вставляем заказ
            order = await conn.fetchrow(
                'INSERT INTO orders (user_id, total_amount) VALUES ($1, $2) RETURNING id',
                user_id, total
            )
            order_id = order['id']

            # Вставляем позиции
            for item in cart_items:
                await conn.execute('''
                    INSERT INTO order_items (order_id, product_id, product_name, price, quantity)
                    VALUES ($1, $2, $3, $4, $5)
                ''', order_id, item['id'], item['name'], item['price'], item['quantity'])

            return order_id


async def get_user_orders(user_id: int):
    """Возвращает все заказы пользователя с деталями"""
    async with pool.acquire() as conn:
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