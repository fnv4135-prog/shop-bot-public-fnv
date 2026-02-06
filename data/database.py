import sqlite3


def init_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            total INTEGER NOT NULL,
            status TEXT DEFAULT 'new'
        )
    ''')

    conn.commit()
    conn.close()
    print('✅ База данных инициализирована')


def add_test_product():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()

    test_products = [
        (1, '📱 iPhone 15', 79900, 'Новый iPhone 15'),
        (2, '💻 MacBook Air', 119900, 'Ноутбук Apple'),
        (3, '🎧 AirPods Pro', 24900, 'Беспроводные наушники'),
    ]

    cursor.execute('DELETE FROM products')

    cursor.executemany(
        'INSERT INTO products (id, name, price, description) VALUES (?, ?, ?, ?)',
        test_products
    )

    conn.commit()
    conn.close()
    print('✅ Тестовые товары добавлены')