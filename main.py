import asyncio
import logging
import os
import sys
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# Импорты роутеров
from handlers.products import router as products_router
from handlers.cart import router as cart_router
from handlers.order import router as order_router

# ================== НАСТРОЙКА ЛОГИРОВАНИЯ ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ================== ЗАЩИТА ОТ МНОЖЕСТВЕННОГО ЗАПУСКА ==================
def check_single_instance():
    """Проверяем, что бот не запущен уже в другом процессе"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 9999))
        sock.listen(5)
        return True
    except socket.error:
        logger.error("⚠️ Бот уже запущен! Закройте все другие экземпляры.")
        return False


# ================== HEALTH CHECK ДЛЯ RENDER ==================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/health', '/ping']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'🛍 Shop Bot is running')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Отключаем логи health check запросов
        pass


def run_http_server():
    """Запуск HTTP сервера для health checks (только на Render)"""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"🌐 HTTP server started on port {port}")
    server.serve_forever()


# ================== ОСНОВНАЯ ФУНКЦИЯ БОТА ==================
async def main():
    try:
        # Проверяем переменные окружения
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            logger.error("❌ BOT_TOKEN не найден!")
            if os.environ.get('ON_RENDER'):
                logger.info("На Render добавьте BOT_TOKEN в Environment Variables")
            sys.exit(1)

        logger.info("🔄 Инициализация бота...")

        # Инициализируем бота
        bot = Bot(token=bot_token)
        dp = Dispatcher(storage=MemoryStorage())

        # Подключаем роутеры
        dp.include_router(products_router)
        dp.include_router(cart_router)
        dp.include_router(order_router)

        # ================== БАЗОВЫЕ КОМАНДЫ ==================
        @dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            await message.answer(
                "🏪 <b>Добро пожаловать в магазин!</b>\n\n"
                "🛍 <b>Доступные команды:</b>\n"
                "/start - Начало работы\n"
                "/products - Показать каталог\n"
                "/cart - Корзина\n"
                "/order - Оформление заказа\n"
                "/help - Помощь\n\n"
                "✨ <i>Просто нажмите на нужную команду!</i>",
                parse_mode="HTML"
            )

        @dp.message(Command("help"))
        async def cmd_help(message: types.Message):
            await message.answer(
                "ℹ️ <b>Помощь по командам:</b>\n\n"
                "🛒 <b>/products</b> - Просмотр каталога товаров\n"
                "🛍 <b>/cart</b> - Просмотр корзины\n"
                "✅ <b>/order</b> - Оформление заказа\n\n"
                "🎯 <i>Или используйте кнопки в меню!</i>",
                parse_mode="HTML"
            )

        # ================== ОБРАБОТКА НЕИЗВЕСТНЫХ СООБЩЕНИЙ ==================
        @dp.message()
        async def handle_unknown_message(message: types.Message):
            """Обработка любых сообщений не-команд"""
            if message.text and not message.text.startswith('/'):
                await message.answer(
                    "🤖 <b>Я понимаю только команды:</b>\n\n"
                    "Используйте /start для начала работы\n"
                    "Или /help для списка команд",
                    parse_mode="HTML"
                )

        # ================== ОБРАБОТКА НЕИЗВЕСТНЫХ CALLBACK-КНОПОК ==================
        @dp.callback_query()
        async def handle_unknown_callback(callback: types.CallbackQuery):
            """Обработка любых callback-запросов"""
            await callback.answer("🔄 Эта кнопка больше не активна. Обновите меню /start")

        # ================== ЗАПУСК БОТА ==================
        # Проверяем подключение
        me = await bot.get_me()
        logger.info(f"✅ Бот @{me.username} успешно запущен!")

        # Удаляем старые вебхуки (если были)
        await bot.delete_webhook(drop_pending_updates=True)

        # Запускаем поллинг
        logger.info("⏳ Запуск polling...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        raise


# ================== ТОЧКА ВХОДА ==================
if __name__ == '__main__':
    # Проверка на множественный запуск
    if not check_single_instance():
        sys.exit(1)

    # Проверяем, запущен ли на Render
    is_render = os.environ.get('ON_RENDER', '').lower() == 'true'

    if is_render:
        logger.info("🌐 Запуск на Render")
        # Запускаем HTTP сервер в отдельном потоке
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