import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_user_orders, add_to_cart

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("order"))
async def cmd_order(message: types.Message):
    """Перенаправление в корзину"""
    from handlers.cart import show_cart_handler
    await show_cart_handler(message)


@router.callback_query(lambda c: c.data == "my_orders")
async def show_my_orders(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        orders = await get_user_orders(user_id)

        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")]
        ])

        if not orders:
            await callback.message.edit_text(
                "📝 <b>История заказов</b>\n\n"
                "У вас пока нет ни одного заказа.\n"
                "Перейдите в каталог, чтобы сделать первый заказ!",
                reply_markup=back_keyboard,
                parse_mode="HTML"
            )
            await callback.answer()
            return

        text = "📝 <b>Ваши последние заказы:</b>\n\n"
        for order in orders[:5]:
            date = order['order_date'].strftime('%d.%m.%Y %H:%M')
            text += f"🆔 #{order['id']} от {date}\n"
            text += f"💰 Сумма: {order['total_amount']}₽, статус: <b>{order['status']}</b>\n"
            items = order['items']
            if items and isinstance(items, list):
                for item in items[:3]:
                    text += f"   • {item['product_name']} x{item['quantity']} – {item['price']}₽\n"
                if len(items) > 3:
                    text += f"   ... и ещё {len(items) - 3} товаров\n"
            # Добавляем кнопку повтора для каждого заказа
            text += f"\n"

        if len(orders) > 5:
            text += f"<i>... и ещё {len(orders) - 5} заказов</i>\n\n"

        # Создаём клавиатуру с кнопками для каждого заказа
        kb = []
        for order in orders[:5]:
            kb.append([InlineKeyboardButton(
                text=f"🔁 Повторить заказ #{order['id']}",
                callback_data=f"repeat_order_{order['id']}"
            )])
        kb.append([InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog")])
        kb.append([InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")])

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.exception(f"🔥 Ошибка в show_my_orders для user {callback.from_user.id}: {e}")
        await callback.answer("Не удалось загрузить заказы. Попробуйте позже.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("repeat_order_"))
async def repeat_order(callback: types.CallbackQuery):
    """Повтор заказа: добавляет все товары из заказа в корзину"""
    order_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    from database.orders import get_order_items_by_order_id

    items = await get_order_items_by_order_id(order_id)
    if not items:
        await callback.answer("Не удалось повторить заказ", show_alert=True)
        return

    # Добавляем каждый товар в корзину
    added = 0
    for item in items:
        success = await add_to_cart(user_id, item['product_id'], item['quantity'])
        if success:
            added += 1

    await callback.answer(f"✅ {added} товаров добавлено в корзину", show_alert=True)
    # Переходим в корзину
    from handlers.cart import show_cart_handler
    await show_cart_handler(callback.message, user_id)