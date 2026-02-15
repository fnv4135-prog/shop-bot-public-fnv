from .connection import pool, init_pool, close_pool
from .models import create_tables, migrate_initial_data
from .products import get_all_products, get_product_by_id, add_product, count_products
from .cart import get_cart_items, add_to_cart, clear_cart, count_carts
from .orders import create_orders_tables, save_order, get_user_orders, get_all_orders_stats   # добавили сюда
from .users import create_users_table, ensure_user

__all__ = [
    'init_pool', 'close_pool', 'create_tables', 'migrate_initial_data',
    'get_all_products', 'get_product_by_id', 'add_product', 'count_products',
    'get_cart_items', 'add_to_cart', 'clear_cart', 'count_carts',
    'create_orders_tables', 'save_order', 'get_user_orders', 'get_all_orders_stats',
    'create_users_table', 'ensure_user', 'get_user_internal_id',
]