from aiogram import Router, types
from aiogram.filters import Command
import config  # добавил для демо-режима (пока не используется)

router = Router()

@router.message(Command("order"))
async def cmd_order(message: types.Message):
    from handlers.cart import show_cart_handler
    await show_cart_handler(message)