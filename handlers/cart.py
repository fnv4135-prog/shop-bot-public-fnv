import logging
import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_cart_items, clear_cart, save_order
from utils import gsheets

logger = logging.getLogger(__name__)
router = Router()


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
    try:
        user_id = callback.from_user.id
        username = callback.from_user.username or ""
        first_name = callback.from_user.first_name or ""
        last_name = callback.from_user.last_name or ""

        cart_items = await get_cart_items(user_id)
        if not cart_items:
            await callback.answer("❌ Корзина пуста!", show_alert=True)
            return

        total = sum(item['price'] * item['quantity'] for item in cart_items)
        total_items = sum(item['quantity'] for item in cart_items)

        # Сохраняем заказ и получаем реальный ID
        order_id = await save_order(
            user_id=user_id,
            cart_items=cart_items,
            total=total,
            username=username,
            first_name=first_name,
            last_name=last_name
        )

        # Очищаем корзину
        success = await clear_cart(user_id)

        # Логируем в Google Sheets (фоново)
        asyncio.create_task(gsheets.log_order_created(
            user_id=user_id,
            username=username,
            order_id=order_id,
            total=total,
            items_count=total_items
        ))

        # Клавиатура для дальнейших действий
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")]
        ])

        if success and order_id:
            await callback.message.edit_text(
                f"🎉 <b>Заказ оформлен!</b>\n\n"
                f"🆔 Номер заказа: #{order_id}\n"
                f"💰 Сумма: {total}₽\n"
                f"📦 Товаров: {total_items}\n\n"
                f"Администратор свяжется с вами для уточнения деталей.\n"
                f"Спасибо за покупку! 🛍",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer("✅ Заказ оформлен!", show_alert=True)
        else:
            await callback.message.edit_text(
                "❌ <b>Ошибка при оформлении заказа</b>\n\nПопробуйте позже.",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer("❌ Ошибка", show_alert=True)

    except Exception as e:
        logger.exception(f"🔥 Критическая ошибка в confirm_order для user {callback.from_user.id}: {e}")
        # Обязательно отвечаем на callback, чтобы кнопка не зависла
        await callback.answer("Произошла внутренняя ошибка. Мы уже знаем о ней.", show_alert=True)
        # Пытаемся сообщить пользователю в чат (если можно)
        try:
            await callback.message.answer("⚠️ Произошла ошибка при оформлении заказа. Попробуйте ещё раз позже.")
        except:
            pass