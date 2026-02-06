import asyncio
import logging
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# Импорты роутеров
from handlers.products import router as products_router
from handlers.cart import router as cart_router
from handlers.order import router as order_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Health check сервер для Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is alive')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Не логируем health check запросы
        pass


async def start_bot():
    """Основная функция запуска бота"""
    try:
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment variables!")
            sys.exit(1)

        bot = Bot(token=bot_token)

        # Проверяем, что бот доступен
        me = await bot.get_me()
        logger.info(f"Bot @{me.username} started successfully")

        # Создаем диспетчер
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        # Базовые команды
        @dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            await message.answer("👋 Добро пожаловать в магазин!\nИспользуйте /menu для просмотра товаров.")

        @dp.message(Command("menu"))
        async def cmd_menu(message: types.Message):
            await message.answer("📋 Меню товаров доступно через кнопки ниже.")

        @dp.message(Command("help"))
        async def cmd_help(message: types.Message):
            await message.answer("ℹ️ Помощь:\n/menu - товары\n/cart - корзина\n/order - заказ")

        # Подключаем роутеры
        dp.include_router(products_router)
        dp.include_router(cart_router)
        dp.include_router(order_router)

        # Удаляем вебхук если был (на всякий случай)
        await bot.delete_webhook(drop_pending_updates=True)

        logger.info("Starting polling...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        raise


def run_http_server():
    """Запуск HTTP сервера для health checks"""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"HTTP server started on port {port}")
    server.serve_forever()


if __name__ == '__main__':
    # Проверяем, что бот не запущен локально
    is_render = os.environ.get('ON_RENDER', '').lower() == 'true'

    if is_render:
        logger.info("Running on Render")
        # Запускаем HTTP сервер в отдельном потоке
        import threading

        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()

    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)