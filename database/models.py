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

        # Категории (если ещё нет, добавим)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                parent_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        # Товары
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                price INTEGER NOT NULL,
                image_url TEXT,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
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

        # Промокоды
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                discount_type VARCHAR(10) NOT NULL CHECK (discount_type IN ('percent', 'fixed')),
                discount_value INTEGER NOT NULL,
                valid_until DATE,
                max_uses INTEGER DEFAULT NULL,
                used_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')

        # Заказы (с добавленным promocode_id)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                total_amount INTEGER NOT NULL,
                promocode_id INTEGER REFERENCES promocodes(id) ON DELETE SET NULL,
                status VARCHAR(50) DEFAULT 'новый',
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

        # Индексы для ускорения
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_promocode ON orders(promocode_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_promocodes_code ON promocodes(code)')

        logger.info("✅ Все таблицы созданы/проверены")


async def migrate_initial_data():
    """Миграция начальных данных"""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Проверяем, есть ли товары
        count = await conn.fetchval("SELECT COUNT(*) FROM products")

        if count == 0:
            # Добавляем тестовые товары (если категорий ещё нет, можно добавить позже через админку)
            # Здесь можно оставить как есть или убрать, если будешь добавлять через админку
            await conn.execute("""
                INSERT INTO products (name, description, price, is_active) VALUES
                ('📱 iPhone 15', 'Новый iPhone 15', 79900, true),
                ('💻 MacBook Air', 'Ноутбук Apple', 119900, true),
                ('🎧 AirPods Pro', 'Беспроводные наушники', 24900, true),
                ('⌚ Apple Watch', 'Умные часы Apple', 39900, true),
                ('🔋 Power Bank', 'Мощный power bank', 4900, true)
            """)
            logger.info(f"✅ Добавлено 5 тестовых товаров")

        return count