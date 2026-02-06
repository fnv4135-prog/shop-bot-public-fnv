from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("order"))
async def cmd_order(message: types.Message):
    # Просто перенаправляем в корзину
    from handlers.cart import show_cart_handler
    await show_cart_handler(message)