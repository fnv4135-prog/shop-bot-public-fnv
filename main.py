import asyncio
import logging
import os
import sys
import threading
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Класс для health check сервера (требуется Render)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running')

    def log_message(self, format, *args):
        # Убираем логирование health check запросов
        pass


# Функция запуска HTTP сервера в отдельном потоке
def run_http_server():
    # Получаем порт из переменных окружения (для Render) или используем 8080
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Starting HTTP server on port {port}")
    server.serve_forever()


# Функция для инициализации бота
async def init_bot():
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN не найден в переменных окружения!")
        sys.exit(1)

    bot = Bot(token=bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация команд
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer("Добро пожаловать в магазин! Используйте /menu для просмотра товаров.")

    @dp.message(Command("menu"))
    async def cmd_menu(message: types.Message):
        await message.answer("Меню товаров доступно через кнопки ниже.")

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        await message.answer("Помощь:\n/menu - просмотр товаров\n/cart - корзина\n/order - оформление заказа")

    # Подключаем роутеры
    dp.include_router(products_router)
    dp.include_router(cart_router)
    dp.include_router(order_router)

    return bot, dp


# Основная асинхронная функция
async def main():
    try:
        bot, dp = await init_bot()

        # Проверка, запущен ли на Render
        on_render = os.environ.get('ON_RENDER', '').lower() == 'true'

        if on_render:
            logger.info("Starting bot on Render with polling...")
            # Удаляем вебхук если был установлен (на случай перезапуска)
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted, starting polling...")
        else:
            logger.info("Starting bot locally...")

        # Запускаем поллинг
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        raise


# Точка входа
if __name__ == '__main__':
    # Запускаем HTTP сервер в отдельном потоке (для Render health checks)
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Запускаем бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")