import asyncio
import sys
import os
from dotenv import load_dotenv  # ДОБАВЬТЕ ЭТУ СТРОКУ

# ЗАГРУЖАЕМ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ИЗ .env ФАЙЛА
load_dotenv()

# Проверяем, загрузилась ли переменная
if not os.getenv('DATABASE_URL'):
    print("❌ ВНИМАНИЕ: DATABASE_URL не найден в .env файле!")
    print("   Проверьте, что файл .env находится в той же папке")
    print("   Содержимое .env должно быть:")
    print(
        "   DATABASE_URL=postgresql://shopuser:пароль@dpg-xxxxx-a.frankfurt-postgres.render.com/shopdb?sslmode=require")
    exit(1)

# Добавляем корневую папку в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test():
    print("🧪 Тестирование новой архитектуры БД...")

    try:
        from database import init_pool, create_tables, migrate_initial_data
        from database.cart import add_to_cart, get_cart_items, clear_cart

        # Инициализация БД
        await init_pool()
        await create_tables()
        count = await migrate_initial_data()
        print(f"✅ БД инициализирована. Товаров: {count}")

        # Тест корзины
        test_user_id = 999999
        await add_to_cart(test_user_id, 1)
        await add_to_cart(test_user_id, 2)

        cart = await get_cart_items(test_user_id)
        print(f"✅ Товаров в корзине: {len(cart)}")

        await clear_cart(test_user_id)
        cart = await get_cart_items(test_user_id)
        print(f"✅ Корзина очищена. Товаров: {len(cart)}")

        print("🎉 Архитектура работает корректно!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())