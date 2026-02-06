from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from handlers.products import user_carts  # Импортируем наше временное хранилище

router = Router()


async def show_cart_handler(message: types.Message, user_id: int = None):
    """Функция для отображения корзины"""
    if user_id is None:
        user_id = message.from_user.id

    # Получаем корзину пользователя
    cart = user_carts.get(user_id, [])

    if not cart:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Перейти в каталог", callback_data="back_to_products")]
        ])

        if hasattr(message, 'edit_text'):
            await message.edit_text(
                "🛒 <b>Ваша корзина пуста</b>\n\n"
                "Добавьте товары из каталога!",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "🛒 <b>Ваша корзина пуста</b>\n\n"
                "Добавьте товары из каталога!",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        return

    # Подсчитываем общую сумму
    total_price = sum(item['price'] for item in cart)

    # Формируем список товаров в корзине
    cart_items_text = ""
    for i, item in enumerate(cart, 1):
        cart_items_text += f"{i}. {item['name']} - {item['price']}₽\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="create_order")],
        [InlineKeyboardButton(text="🔙 Назад к каталогу", callback_data="back_to_products")]
    ])

    if hasattr(message, 'edit_text'):
        await message.edit_text(
            f"🛒 <b>Ваша корзина:</b>\n\n"
            f"{cart_items_text}\n"
            f"<b>Итого: {total_price}₽</b>\n"
            f"<b>Товаров: {len(cart)}</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"🛒 <b>Ваша корзина:</b>\n\n"
            f"{cart_items_text}\n"
            f"<b>Итого: {total_price}₽</b>\n"
            f"<b>Товаров: {len(cart)}</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@router.message(Command("cart"))
async def cmd_cart(message: types.Message):
    await show_cart_handler(message)


@router.callback_query(F.data == "show_cart")
async def callback_show_cart(callback: types.CallbackQuery):
    await show_cart_handler(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_carts[user_id] = []  # Очищаем корзину

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Перейти в каталог", callback_data="back_to_products")]
    ])

    await callback.message.edit_text(
        "🗑 <b>Корзина очищена!</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer("Корзина очищена!", show_alert=False)