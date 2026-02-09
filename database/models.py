"""
database/models.py - Создание и миграция таблиц
"""

from .connection import get_pool
import logging

logger = logging.getLogger(__name__)


async def create_tables():
    """Создание всех таблиц"""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Пользователи
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(100),
                full_name VARCHAR(200),
                created_at TIMESTAMP DEFAULT NOW(),
                last_seen TIMESTAMP DEFAULT NOW()
            )
        ''')

        # Товары - ДОБАВЛЯЕМ ПОЛЕ category!
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                price INTEGER NOT NULL,
                image_url TEXT,
                category VARCHAR(100) DEFAULT 'Без категории',  -- ← ДОБАВЛЕНО
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')

        # Корзины
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS cart_items (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                quantity INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, product_id)
            )
        ''')

        # Заказы
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                total_amount INTEGER NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                order_number VARCHAR(100) UNIQUE,
                customer_name VARCHAR(200),
                customer_phone VARCHAR(20),
                customer_address TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        # Товары в заказах
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id),
                product_name VARCHAR(200) NOT NULL,
                product_price INTEGER NOT NULL,
                quantity INTEGER NOT NULL
            )
        ''')

        await conn.execute("""
                    DO $$ 
                    BEGIN 
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                       WHERE table_name='products' AND column_name='category') THEN
                            ALTER TABLE products ADD COLUMN category VARCHAR(100) DEFAULT 'Без категории';
                        END IF;
                    END $$;
                """)

        logger.info("✅ Поле category в таблице products проверено/добавлено")
        logger.info("✅ Таблицы созданы/проверены")


async def migrate_initial_data():
    """Миграция начальных данных"""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Проверяем, есть ли товары
        count = await conn.fetchval("SELECT COUNT(*) FROM products")

        if count == 0:
            # Добавляем тестовые товары С КАТЕГОРИЯМИ
            await conn.execute("""
                INSERT INTO products (name, description, price, category) VALUES
                ('📱 iPhone 15', 'Новый iPhone 15', 79900, 'Смартфоны'),
                ('💻 MacBook Air', 'Ноутбук Apple', 119900, 'Ноутбуки'),
                ('🎧 AirPods Pro', 'Беспроводные наушники', 24900, 'Аксессуары'),
                ('⌚ Apple Watch', 'Умные часы Apple', 39900, 'Гаджеты'),
                ('🔋 Power Bank', 'Мощный power bank', 4900, 'Аксессуары')
            """)
            logger.info(f"✅ Добавлено 5 тестовых товаров с категориями")

        return count