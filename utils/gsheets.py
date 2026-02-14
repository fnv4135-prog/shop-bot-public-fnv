import asyncio
import base64
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

_gc: Optional[gspread.Client] = None
_worksheet: Optional[gspread.Worksheet] = None
_init_lock = asyncio.Lock()


async def init_google_sheets():
    global _gc, _worksheet

    async with _init_lock:
        if _gc is not None and _worksheet is not None:
            return True

        if os.getenv('GOOGLE_SHEETS_ENABLED', 'true').lower() != 'true':
            logger.info("📊 Google Sheets аналитика отключена")
            return False

        creds_base64 = os.getenv('GOOGLE_CREDENTIALS_BASE64')
        if not creds_base64:
            logger.warning("⚠️ GOOGLE_CREDENTIALS_BASE64 не найден, аналитика не работает")
            return False

        sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'shop_bot_logs')
        sheet_id = os.getenv('GOOGLE_SHEET_ID', None)

        try:
            creds_json = base64.b64decode(creds_base64).decode('utf-8')
            creds_dict = json.loads(creds_json)
            credentials = Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )

            loop = asyncio.get_event_loop()
            gc = await loop.run_in_executor(None, lambda: gspread.authorize(credentials))

            if sheet_id:
                sh = await loop.run_in_executor(None, gc.open_by_key, sheet_id)
            else:
                try:
                    sh = await loop.run_in_executor(None, gc.open, sheet_name)
                except gspread.SpreadsheetNotFound:
                    sh = await loop.run_in_executor(None, gc.create, sheet_name)
                    logger.info(f"📊 Создана новая таблица: {sheet_name}")

            try:
                worksheet = await loop.run_in_executor(None, sh.get_worksheet, 0)
            except:
                worksheet = await loop.run_in_executor(None, sh.add_worksheet, "Логи", 1000, 20)

            if not await loop.run_in_executor(None, worksheet.get_all_values):
                headers = ["timestamp", "event", "user_id", "username", "data"]
                await loop.run_in_executor(None, worksheet.append_row, headers)

            _gc = gc
            _worksheet = worksheet
            logger.info("✅ Google Sheets аналитика инициализирована")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Google Sheets: {e}")
            return False


async def log_event(event: str, user_id: int, username: str = "", data: Dict[str, Any] = None):
    if not _worksheet:
        asyncio.create_task(init_google_sheets())
        return

    if data is None:
        data = {}

    timestamp = datetime.now().isoformat()
    row = [
        timestamp,
        event,
        str(user_id),
        username,
        json.dumps(data, ensure_ascii=False)
    ]

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _worksheet.append_row, row)
        logger.debug(f"📊 Событие {event} записано в Google Sheets")
    except Exception as e:
        logger.error(f"❌ Ошибка записи в Google Sheets: {e}")


async def log_start(user_id: int, username: str = ""):
    await log_event("start", user_id, username)


async def log_add_to_cart(user_id: int, username: str, product_id: int, product_name: str, quantity: int = 1):
    data = {
        "product_id": product_id,
        "product_name": product_name,
        "quantity": quantity
    }
    await log_event("add_to_cart", user_id, username, data)


async def log_order_created(user_id: int, username: str, order_id: int, total: float, items_count: int):
    data = {
        "order_id": order_id,
        "total": total,
        "items_count": items_count
    }
    await log_event("order_created", user_id, username, data)


async def log_order_canceled(user_id: int, username: str, order_id: int):
    data = {"order_id": order_id}
    await log_event("order_canceled", user_id, username, data)


async def log_cart_cleared(user_id: int, username: str):
    await log_event("cart_cleared", user_id, username)