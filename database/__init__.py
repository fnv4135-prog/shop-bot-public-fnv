# database/__init__.py
from .connection import init_pool, close_pool
from .models import create_tables, migrate_initial_data
from .products import get_all_products, get_product_by_id, add_product, count_products
from .cart import get_cart_items, add_to_cart, clear_cart

__all__ = [
    # Подключение
    'init_pool', 'close_pool', 'create_tables', 'migrate_initial_data',

    # Товары
    'get_all_products', 'get_product_by_id', 'add_product', 'count_products',

    # Корзина
    'get_cart_items', 'add_to_cart', 'clear_cart',
]