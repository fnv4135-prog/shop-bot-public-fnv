from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Импортируем наше временное хранилище
from handlers.products import user_carts, products

router = Router()


async def show_cart_handler(message: types.Message, user_id: int = None):
    """Функция для отображения корзины"""
    if user_id is None:
        user_id = message.from_user.id

    cart = user_carts.get(user_id, [])

    if not cart:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 В каталог", callback_data="back_to_products")],
            [InlineKeyboardButton(text="🔙 Главная", callback_data="go_start")]
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

    # Подсчитываем
    total_price = sum(item['price'] for item in cart)

    # Формируем список
    cart_items_text = ""
    for i, item in enumerate(cart, 1):
        cart_items_text += f"{i}. {item['name']} - {item['price']}₽\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="create_order")],
        [
            InlineKeyboardButton(text="🛍 В каталог", callback_data="back_to_products"),
            InlineKeyboardButton(text="🔙 Главная", callback_data="go_start")
        ]
    ])

    text = (
        f"🛒 <b>Ваша корзина:</b>\n\n"
        f"{cart_items_text}\n"
        f"<b>Товаров: {len(cart)}</b>\n"
        f"<b>Итого: {total_price}₽</b>"
    )

    if hasattr(message, 'edit_text'):
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


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
    user_carts[user_id] = []

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 В каталог", callback_data="back_to_products")],
        [InlineKeyboardButton(text="🔙 Главная", callback_data="go_start")]
    ])

    await callback.message.edit_text(
        "🗑 <b>Корзина очищена!</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer("Корзина очищена!", show_alert=False)


@router.callback_query(F.data == "create_order")
async def create_order(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    total_price = sum(item['price'] for item in cart)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="show_cart")]
    ])

    await callback.message.edit_text(
        f"✅ <b>Оформление заказа</b>\n\n"
        f"Товаров: {len(cart)}\n"
        f"Сумма: {total_price}₽\n\n"
        f"Для оформления нажмите 'Подтвердить заказ'.\n"
        f"Администратор свяжется с вами в ближайшее время.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_order")
async def confirm_order(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    total_price = sum(item['price'] for item in cart)

    # Очищаем корзину после заказа
    user_carts[user_id] = []

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 В каталог", callback_data="back_to_products")],
        [InlineKeyboardButton(text="🔙 Главная", callback_data="go_start")]
    ])

    await callback.message.edit_text(
        f"🎉 <b>Заказ оформлен!</b>\n\n"
        f"Номер заказа: #{user_id}{len(cart)}\n"
        f"Сумма: {total_price}₽\n"
        f"Товаров: {len(cart)}\n\n"
        f"Администратор свяжется с вами для уточнения деталей.\n"
        f"Спасибо за покупку! 🛍",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer("Заказ оформлен! Администратор свяжется с вами.", show_alert=True)