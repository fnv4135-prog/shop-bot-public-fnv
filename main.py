# В начале файла добавляем импорты
import asyncio
import logging
import os
import sys
import socket
from dotenv import load_dotenv
import config
from utils import gsheets

load_dotenv()

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# ================== ИМПОРТ РОУТЕРОВ ==================
from handlers.admin import router as admin_router
from handlers.products import router as products_router
from handlers.cart import router as cart_router
from handlers.order import router as order_router
from handlers.search import router as search_router

# ================== ИМПОРТ УТИЛИТ ==================
from utils.http_server import run_http_server
from utils.cleanup import cleanup_old_sessions
from utils.debug_handlers import setup_global_handlers

# ================== ИМПОРТ USERS ==================
from database import create_users_table

# ================== НАСТРОЙКА ЛОГИРОВАНИЯ ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ================== ЗАЩИТА ОТ МНОЖЕСТВЕННОГО ЗАПУСКА ==================
def check_single_instance():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 9999))
        sock.listen(5)
        logger.info("✅ Проверка на множественный запуск пройдена")
        return True
    except socket.error:
        logger.error("⚠️ Бот уже запущен! Закройте все другие экземпляры.")
        return False


# ================== ОБРАБОТЧИКИ ЗАВЕРШЕНИЯ РАБОТЫ ==================
async def on_shutdown():
    logger.info("🔄 Завершение работы бота...")
    try:
        from database import close_pool
        await close_pool()
        logger.info("📴 Подключение к БД закрыто")
    except Exception as e:
        logger.error(f"Ошибка при закрытии БД: {e}")


async def main():
    try:
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            logger.error("❌ BOT_TOKEN не найден!")
            sys.exit(1)

        logger.info("🔄 Инициализация бота...")

        # ПОДКЛЮЧАЕМ БАЗУ ДАННЫХ
        try:
            from database import init_pool, create_tables, migrate_initial_data
            from database import create_orders_tables  # импорт вверху
            await init_pool()
            await create_users_table()
            await create_tables()
            await create_orders_tables()
            initial_count = await migrate_initial_data()
            logger.info(f"✅ База данных подключена. Товаров в БД: {initial_count}")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise


        await cleanup_old_sessions(bot_token)
        await asyncio.sleep(1)

        bot = Bot(token=bot_token)
        dp = Dispatcher(storage=MemoryStorage())

        dp.shutdown.register(on_shutdown)

        dp.include_router(products_router)  # товары и категории
        dp.include_router(cart_router)  # корзина
        dp.include_router(order_router)  # заказы
        dp.include_router(search_router)  # поиск (после основных)
        dp.include_router(admin_router)  # админка (в конце)

        await setup_global_handlers(dp)

        # Инициализация Google Sheets (если включено)
        if config.GOOGLE_SHEETS_ENABLED:
            asyncio.create_task(gsheets.init_google_sheets())

        # ================== ГЛАВНОЕ МЕНЮ НА КНОПКАХ ==================
        @dp.message(Command("start", "help", "menu"))
        async def unified_menu_handler(message: types.Message):
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🛒 Каталог товаров", callback_data="show_catalog")],
                [types.InlineKeyboardButton(text="📦 Моя корзина", callback_data="view_cart"),
                 types.InlineKeyboardButton(text="🔍 Поиск товаров", callback_data="search")],  # две кнопки в ряду
                [types.InlineKeyboardButton(text="📝 Мои заказы", callback_data="my_orders")],
                [types.InlineKeyboardButton(text="❓ Помощь / О нас", callback_data="help_info")]
            ])

            welcome_text = (
                "🏪 <b>Добро пожаловать в магазин электроники SMART-TECH!</b>\n\n"
                "🎯 <b>Выберите действие:</b>\n\n"
                "• <b>🛒 Каталог</b> — выбор товаров по категориям\n"
                "• <b>🔍 Поиск</b> — поиск товара по названию\n"
                "• <b>📦 Корзина</b> — просмотр и оформление заказа\n"
                "• <b>📝 Мои заказы</b> — история ваших покупок\n"
                "• <b>❓ Помощь</b> — информация о доставке и оплате\n\n"
                "✨ <i>Просто нажмите на нужную кнопку!</i>"
            )

            await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
            logger.info(f"📱 Пользователь {message.from_user.id} открыл главное меню")
            asyncio.create_task(gsheets.log_start(message.from_user.id, message.from_user.username or ""))

        # ================== ОБРАБОТЧИКИ КНОПОК МЕНЮ ==================
        @dp.callback_query(lambda c: c.data == "go_home")
        async def go_home_handler(callback: types.CallbackQuery):
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🛒 Каталог товаров", callback_data="show_catalog")],
                [types.InlineKeyboardButton(text="📦 Моя корзина", callback_data="view_cart"),
                 types.InlineKeyboardButton(text="🔍 Поиск товаров", callback_data="search")],  # две кнопки в ряду
                [types.InlineKeyboardButton(text="📝 Мои заказы", callback_data="my_orders")],
                [types.InlineKeyboardButton(text="❓ Помощь / О нас", callback_data="help_info")]
            ])

            welcome_text = (
                "🎯 <b>Выберите действие:</b>\n\n"
                "• <b>🛒 Каталог</b> — выбор товаров по категориям\n"
                "• <b>🔍 Поиск</b> — поиск товара по названию\n"
                "• <b>📦 Корзина</b> — просмотр и оформление заказа\n"
                "• <b>📝 Мои заказы</b> — история ваших покупок\n"
                "• <b>❓ Помощь</b> — информация о доставке и оплате\n\n"
                "✨ <i>Просто нажмите на нужную кнопку!</i>"
            )

            await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            logger.info(f"🔼 Пользователь {callback.from_user.id} вернулся в главное меню")

        @dp.callback_query(lambda c: c.data == "help_info")
        async def help_info_handler(callback: types.CallbackQuery):
            help_text = (
                "❓ <b>Помощь и информация</b>\n\n"
                "🛒 <b>Как сделать заказ:</b>\n"
                "1. Перейдите в <b>Каталог товаров</b>\n"
                "2. Выберите товар и добавьте в корзину\n"
                "3. Перейдите в <b>Корзину</b> для оформления\n\n"
                "💰 <b>Оплата:</b> Предоплата 100% переводом на карту\n\n"
                "🚚 <b>Доставка:</b> По Хабаровску — бесплатно, в регионы — по тарифам ТК\n\n"
                "⏰ <b>Часы работы:</b> Ежедневно с 9:00 до 21:00\n\n"
                "📞 <b>Контакты:</b> @nicholasbiz (основной канал связи)\n\n"
                "🔧 <b>Техподдержка:</b> Если что-то не работает, напишите нам!"
            )

            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="go_home")]
            ])

            await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            logger.info(f"❓ Пользователь {callback.from_user.id} открыл раздел помощи")


        # ================== ЗАПУСК И ПРОВЕРКИ ==================
        me = await bot.get_me()
        logger.info(f"✅ Бот @{me.username} успешно запущен!")

        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Вебхуки удалены")

        logger.info("⏳ Запуск polling...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        raise


if __name__ == '__main__':
    if not check_single_instance():
        sys.exit(1)

    is_render = os.environ.get('ON_RENDER', '').lower() == 'true'

    if is_render:
        logger.info("🌐 Запуск на Render")
        import threading
        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()
    else:
        logger.info("💻 Локальный запуск")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)