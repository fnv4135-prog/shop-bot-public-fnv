import asyncio
import logging
import os
import sys
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from handlers.admin import router as admin_router

load_dotenv()

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# ================== ИМПОРТ РОУТЕРОВ ==================
# Существующие роутеры
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
        logger.info("✅ Проверка на множественный запуск пройдена")
        return True
    except socket.error:
        logger.error("⚠️ Бот уже запущен! Закройте все другие экземпляры.")
        logger.error("Выполните команды остановки:")
        logger.error("  Windows: taskkill /f /im python.exe")
        logger.error("  Git Bash: pkill -f python")
        return False


# ================== ПРИНУДИТЕЛЬНОЕ ЗАВЕРШЕНИЕ СТАРЫХ СЕССИЙ ==================
async def cleanup_old_sessions(bot_token: str):
    """Принудительно завершаем все старые сессии бота"""
    try:
        logger.info("🔄 Очистка старых сессий бота...")

        # Создаем временного бота для очистки
        temp_bot = Bot(token=bot_token)

        # Удаляем вебхук (если был)
        try:
            await temp_bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Старые вебхуки удалены")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить вебхук: {e}")

        # Закрываем сессию
        try:
            await temp_bot.session.close()
            logger.info("✅ Сессия закрыта")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось закрыть сессию: {e}")

        # Даем время на завершение
        await asyncio.sleep(2)

    except Exception as e:
        logger.warning(f"⚠️ Ошибка при очистке сессий: {e}")


# ================== HEALTH CHECK ДЛЯ RENDER ==================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/health', '/ping']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Shop Bot is running')
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


# ================== ГЛОБАЛЬНЫЕ ОБРАБОТЧИКИ ДЛЯ ОТЛАДКИ ==================
async def setup_global_handlers(dp: Dispatcher):
    """Настройка глобальных обработчиков (заглушка)"""
    # Здесь можно добавить глобальные middleware или фильтры
    pass


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

        # ОЧИСТКА СТАРЫХ СЕССИЙ ПЕРЕД ЗАПУСКОМ
        await cleanup_old_sessions(bot_token)

        # Даем время на очистку
        await asyncio.sleep(3)

        # Инициализируем бота
        bot = Bot(token=bot_token)
        dp = Dispatcher(storage=MemoryStorage())

        # Подключаем роутеры
        dp.include_router(products_router)
        dp.include_router(cart_router)
        dp.include_router(order_router)
        dp.include_router(admin_router)

        # Настраиваем глобальные обработчики для отладки
        await setup_global_handlers(dp)

        # ================== НОВОЕ: ГЛАВНОЕ МЕНЮ НА КНОПКАХ ==================
        # Вместо старого текстового меню создаем единый обработчик с инлайн-клавиатурой
        # Этот обработчик реагирует на команды /start, /help, /menu

        @dp.message(Command("start", "help", "menu"))
        async def unified_menu_handler(message: types.Message):
            """ЕДИНЫЙ ОБРАБОТЧИК ГЛАВНОГО МЕНЮ (заменяет старые cmd_start и cmd_help)"""

            # Создаем клавиатуру с кнопками
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                # Ряд 1: Основные функции
                [types.InlineKeyboardButton(text="🛒 Каталог товаров", callback_data="show_catalog")],
                # Ряд 2: Вспомогательные функции
                [types.InlineKeyboardButton(text="📦 Моя корзина", callback_data="view_cart"),
                 types.InlineKeyboardButton(text="📝 Мои заказы", callback_data="my_orders")],
                # Ряд 3: Информация
                [types.InlineKeyboardButton(text="❓ Помощь / О нас", callback_data="help_info")]
            ])

            # Текст главного меню
            welcome_text = (
                "🏪 <b>Добро пожаловать в магазин электроники FN-Tech!</b>\n\n"
                "🎯 <b>Выберите действие:</b>\n\n"
                "• <b>🛒 Каталог</b> — выбор товаров по категориям\n"
                "• <b>📦 Корзина</b> — просмотр и оформление заказа\n"
                "• <b>📝 Мои заказы</b> — история ваших покупок\n"
                "• <b>❓ Помощь</b> — информация о доставке и оплате\n\n"
                "✨ <i>Просто нажмите на нужную кнопку!</i>"
            )

            # Отправляем сообщение с клавиатурой
            await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
            logger.info(f"📱 Пользователь {message.from_user.id} открыл главное меню")

        # ================== НОВОЕ: ОБРАБОТЧИКИ КНОПОК МЕНЮ ==================

        @dp.callback_query(lambda c: c.data == "go_home")
        async def go_home_handler(callback: types.CallbackQuery):
            """ОБРАБОТЧИК КНОПКИ 'ГЛАВНАЯ' - возврат в главное меню из любого раздела"""
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🛒 Каталог товаров", callback_data="show_catalog")],
                [types.InlineKeyboardButton(text="📦 Моя корзина", callback_data="view_cart"),
                 types.InlineKeyboardButton(text="📝 Мои заказы", callback_data="my_orders")],
                [types.InlineKeyboardButton(text="❓ Помощь / О нас", callback_data="help_info")]
            ])

            welcome_text = (
                "🏪 <b>Главное меню</b>\n\n"
                "🎯 <b>Выберите действие:</b>\n\n"
                "• <b>🛒 Каталог</b> — выбор товаров по категориям\n"
                "• <b>📦 Корзина</b> — просмотр и оформление заказа\n"
                "• <b>📝 Мои заказы</b> — история ваших покупок\n"
                "• <b>❓ Помощь</b> — информация о доставке и оплате"
            )

            # Редактируем существующее сообщение (меняем текст и кнопки)
            await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()  # Убираем "часики" у кнопки
            logger.info(f"🔼 Пользователь {callback.from_user.id} вернулся в главное меню")

        @dp.callback_query(lambda c: c.data == "help_info")
        async def help_info_handler(callback: types.CallbackQuery):
            """ОБРАБОТЧИК КНОПКИ 'ПОМОЩЬ' - показывает информацию о магазине"""
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

            # Кнопка для возврата в меню
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="go_home")]
            ])

            await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            logger.info(f"❓ Пользователь {callback.from_user.id} открыл раздел помощи")

        @dp.callback_query(lambda c: c.data == "my_orders")
        async def my_orders_handler(callback: types.CallbackQuery):
            """ЗАГЛУШКА ДЛЯ РАЗДЕЛА 'МОИ ЗАКАЗЫ' (будет реализовано позже)"""
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="go_home")]
            ])

            await callback.message.edit_text(
                "📝 <b>История заказов</b>\n\n"
                "⏳ <i>Этот раздел находится в активной разработке.</i>\n\n"
                "Скоро здесь появится:\n"
                "• Полная история ваших покупок\n"
                "• Статусы текущих заказов\n"
                "• Возможность повторить заказ\n\n"
                "Следите за обновлениями!",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer("Раздел в разработке", show_alert=False)
            logger.info(f"📝 Пользователь {callback.from_user.id} открыл раздел 'Мои заказы'")

        # ================== СУЩЕСТВУЮЩАЯ ЛОГИКА (без изменений) ==================
        # Старый обработчик кнопки "Главная" (оставлен для совместимости со старыми сообщениями)
        @dp.callback_query(lambda c: c.data == "go_home")
        async def old_go_home_handler(callback: types.CallbackQuery):
            """СТАРЫЙ ОБРАБОТЧИК (для совместимости) - удалите через 2 недели"""
            # Перенаправляем на новый обработчик
            await go_home_handler(callback)

        # ================== ЗАПУСК И ПРОВЕРКИ ==================
        # Проверяем подключение
        me = await bot.get_me()
        logger.info(f"✅ Бот @{me.username} успешно запущен!")

        # Удаляем вебхуки еще раз (на всякий случай)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Вебхуки удалены")

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