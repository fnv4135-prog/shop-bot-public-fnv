import asyncio
import logging
import os
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


# Простой HTTP обработчик для Render
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        # БЕЗ ЭМОДЗИ - только ASCII символы
        self.wfile.write(b'Bot is running')

    def log_message(self, format, *args):
        pass  # Отключаем логи HTTP


def run_http_server(port=8080):
    """Запуск HTTP сервера в отдельном потоке"""
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"🌐 HTTP сервер запущен на порту {port}")
    server.serve_forever()


# Получаем токен
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logging.error("❌ BOT_TOKEN не найден!")
    exit(1)

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Подключаем роутеры
dp.include_router(products_router)
dp.include_router(cart_router)
dp.include_router(order_router)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🏪 **Добро пожаловать в магазин!**\n\n"
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/products - Показать каталог\n"
        "/cart - Корзина\n"
        "/help - Помощь"
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 **Помощь по боту:**\n\n"
        "1. Нажмите /products чтобы посмотреть каталог\n"
        "2. Выберите товар и добавьте в корзину\n"
        "3. Нажмите /cart чтобы оформить заказ\n"
        "4. Следуйте инструкциям для оформления"
    )


async def main():
    logging.basicConfig(level=logging.INFO)

    # Запускаем HTTP сервер в отдельном потоке
    port = int(os.environ.get('PORT', 8080))
    http_thread = threading.Thread(target=run_http_server, args=(port,))
    http_thread.daemon = True
    http_thread.start()

    print(f"🤖 Бот запускается на порту {port}...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())