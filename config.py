import os
from typing import Optional

# Режим демо (если True, уведомления админу не отправляются)
DEMO_MODE = os.getenv('DEMO_MODE', 'false').lower() == 'true'

# ID администратора (твой Telegram ID)
ADMIN_ID = 524082641

GOOGLE_SHEETS_ENABLED = os.getenv('GOOGLE_SHEETS_ENABLED', 'true').lower() == 'true'
GOOGLE_CREDENTIALS_BASE64 = os.getenv('GOOGLE_CREDENTIALS_BASE64', '')
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', 'shop_bot_logs')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '')

def is_demo_mode() -> bool:
    return DEMO_MODE