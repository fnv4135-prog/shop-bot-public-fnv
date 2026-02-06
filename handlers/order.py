from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

@router.message(Command("order"))
async def cmd_order(message: types.Message):
    # Перенаправляем в корзину для оформления заказа
    from handlers.cart import show_cart_handler
    await show_cart_handler(message)