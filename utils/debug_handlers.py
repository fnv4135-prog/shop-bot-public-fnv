# utils/debug_handlers.py
import logging
import os
from aiogram import Dispatcher
from aiogram.filters import Command

logger = logging.getLogger(__name__)


async def setup_global_handlers(dp: Dispatcher):
    """Настройка глобальных обработчиков для отладки"""

    @dp.message(Command("debug"))
    async def debug_info(message):
        """Отладочная информация"""
        info = (
            f"🖥 <b>Отладочная информация</b>\n\n"
            f"👤 <b>Пользователь:</b> {message.from_user.id}\n"
            f"📛 <b>Имя:</b> {message.from_user.full_name}\n"
            f"🌐 <b>Render:</b> {'Да' if os.environ.get('ON_RENDER') else 'Нет'}\n"
            f"🔧 <b>Режим:</b> Production\n"
            f"⚡ <b>Бот работает!</b>"
        )

        await message.answer(info, parse_mode="HTML")
        logger.info(f"Отладочная информация отправлена пользователю {message.from_user.id}")

    @dp.message(Command("id"))
    async def get_user_id(message):
        """Получить свой ID"""
        await message.answer(f"🆔 Ваш ID: <code>{message.from_user.id}</code>", parse_mode="HTML")

    logger.info("✅ Глобальные обработчики отладки настроены")