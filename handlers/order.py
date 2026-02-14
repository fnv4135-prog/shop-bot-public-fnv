import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_user_orders

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("order"))
async def cmd_order(message: types.Message):
    """Перенаправление в корзину"""
    from handlers.cart import show_cart_handler
    await show_cart_handler(message)


@router.callback_query(lambda c: c.data == "my_orders")
async def show_my_orders(callback: types.CallbackQuery):
    """Показывает историю заказов пользователя"""
    user_id = callback.from_user.id
    orders = await get_user_orders(user_id)

    if not orders:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")]
        ])
        await callback.message.edit_text(
            "📝 <b>История заказов</b>\n\n"
            "У вас пока нет ни одного заказа.\n"
            "Перейдите в каталог, чтобы сделать первый заказ!",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = "📝 <b>Ваши последние заказы:</b>\n\n"
    for order in orders[:5]:
        date = order['order_date'].strftime('%d.%m.%Y %H:%M')
        text += f"🆔 #{order['id']} от {date}\n"
        text += f"💰 Сумма: {order['total_amount']}₽, статус: {order['status']}\n"
        items = order['items']
        if items and isinstance(items, list):
            for item in items[:3]:
                text += f"   • {item['product_name']} x{item['quantity']} – {item['price']}₽\n"
            if len(items) > 3:
                text += f"   ... и ещё {len(items) - 3} товаров\n"
        text += "\n"

    if len(orders) > 5:
        text += f"<i>... и ещё {len(orders) - 5} заказов</i>\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog")],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()