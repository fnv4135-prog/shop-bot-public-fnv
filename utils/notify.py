# utils/notify.py
import logging
from aiogram import Bot
from config import ADMIN_ID

logger = logging.getLogger(__name__)

async def notify_admin(bot: Bot, text: str, parse_mode: str = "HTML"):
    try:
        await bot.send_message(ADMIN_ID, text, parse_mode=parse_mode)
        logger.info("Уведомление администратору отправлено")
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление администратору: {e}")