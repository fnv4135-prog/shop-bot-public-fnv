import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_cart_items, clear_cart

router = Router()
logger = logging.getLogger(__name__)


async def show_cart_handler(message: types.Message, user_id: int = None):
    """Показать корзину пользователя"""
    if user_id is None:
        user_id = message.from_user.id

    # Получаем товары в корзине из БД (АСИНХРОННО!)
    cart_items = await get_cart_items(user_id)

    if not cart_items:  # ← Исправлено: было `if not cart`, теперь `if not cart_items`
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")]
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

    # Подсчитываем общую сумму и количество товаров
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    total_items = sum(item['quantity'] for item in cart_items)

    # Формируем текст корзины
    cart_text = "🛒 <b>Ваша корзина:</b>\n\n"
    for i, item in enumerate(cart_items, 1):
        cart_text += f"{i}. {item['name']} - {item['price']}₽ × {item['quantity']}\n"

    cart_text += f"\n<b>Товаров: {total_items}</b>\n<b>Итого: {total}₽</b>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="create_order")],
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="ask_clear_cart")],
        [
            InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")
        ]
    ])

    if hasattr(message, 'edit_text'):
        await message.edit_text(cart_text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(cart_text, reply_markup=keyboard, parse_mode="HTML")


@router.message(Command("cart"))
async def cmd_cart(message: types.Message):
    await show_cart_handler(message)


@router.callback_query(lambda c: c.data == "view_cart")
async def callback_show_cart(callback: types.CallbackQuery):
    """Показать корзину при нажатии на кнопку"""
    await show_cart_handler(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(lambda c: c.data == "ask_clear_cart")
async def ask_clear_cart(callback: types.CallbackQuery):
    """Спросить подтверждение на очистку корзины"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Да, очистить корзину", callback_data="confirm_clear_cart")],
        [InlineKeyboardButton(text="↩️ Нет, вернуться", callback_data="view_cart")]
    ])

    await callback.message.edit_text(
        "⚠️ <b>Вы уверены, что хотите очистить корзину?</b>\n\n"
        "Все товары будут удалены без возможности восстановления.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "confirm_clear_cart")
async def confirm_clear_cart(callback: types.CallbackQuery):
    """Подтверждённая очистка корзины"""
    user_id = callback.from_user.id
    success = await clear_cart(user_id)  # ← Исправлено: добавлено await, функция из database.cart

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog")],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")]
    ])

    if success:
        await callback.message.edit_text(
            "🗑 <b>Корзина очищена!</b>\n\n"
            "Все товары удалены.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка при очистке корзины</b>\n\n"
            "Попробуйте позже.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    await callback.answer("Корзина очищена!" if success else "Ошибка", show_alert=False)


@router.callback_query(lambda c: c.data == "create_order")
async def create_order(callback: types.CallbackQuery):
    """Оформление заказа"""
    user_id = callback.from_user.id

    # Получаем корзину из БД
    cart_items = await get_cart_items(user_id)

    if not cart_items:
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    total = sum(item['price'] * item['quantity'] for item in cart_items)
    total_items = sum(item['quantity'] for item in cart_items)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton(text="🔙 Назад в корзину", callback_data="view_cart")]
    ])

    await callback.message.edit_text(
        f"✅ <b>Оформление заказа</b>\n\n"
        f"Товаров: {total_items}\n"
        f"Сумма: {total}₽\n\n"
        f"Для оформления нажмите 'Подтвердить заказ'.\n"
        f"Администратор свяжется с вами в ближайшее время.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "confirm_order")
async def confirm_order(callback: types.CallbackQuery):
    """Подтверждение заказа"""
    user_id = callback.from_user.id

    # Получаем корзину из БД
    cart_items = await get_cart_items(user_id)

    if not cart_items:
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    total = sum(item['price'] * item['quantity'] for item in cart_items)
    total_items = sum(item['quantity'] for item in cart_items)

    # Очищаем корзину в БД
    success = await clear_cart(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog")],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")]
    ])

    if success:
        await callback.message.edit_text(
            f"🎉 <b>Заказ оформлен!</b>\n\n"
            f"Номер заказа: #{user_id}{total_items}\n"
            f"Сумма: {total}₽\n"
            f"Товаров: {total_items}\n\n"
            f"Администратор свяжется с вами для уточнения деталей.\n"
            f"Спасибо за покупку! 🛍",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer("Заказ оформлен! Администратор свяжется с вами.", show_alert=True)
    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка при оформлении заказа</b>\n\n"
            "Попробуйте позже.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer("Ошибка при оформлении заказа", show_alert=True)


@router.callback_query(lambda c: c.data == "back_to_products")
async def back_to_products(callback: types.CallbackQuery):
    """Вернуться в каталог товаров"""
    from handlers.products import show_products
    await show_products(callback.message)
    await callback.answer()