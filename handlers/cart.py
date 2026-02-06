from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from handlers.products import user_carts

router = Router()


async def show_cart_handler(message: types.Message, user_id: int = None):
    if user_id is None:
        user_id = message.from_user.id

    cart = user_carts.get(user_id, [])

    if not cart:
        builder = InlineKeyboardBuilder()
        builder.button(text="🛍 В каталог", callback_data="back_to_products")
        builder.button(text="🏠 Главная", callback_data="main_menu")
        builder.adjust(1)

        text = "🛒 <b>Ваша корзина пуста</b>\n\nДобавьте товары из каталога!"

        if hasattr(message, 'edit_text'):
            await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        return

    # Подсчитываем
    total = sum(item['price'] for item in cart)

    # Формируем текст
    cart_text = "🛒 <b>Ваша корзина:</b>\n\n"
    for i, item in enumerate(cart, 1):
        cart_text += f"{i}. {item['name']} - {item['price']}₽\n"

    cart_text += f"\n<b>Товаров: {len(cart)}</b>\n<b>Итого: {total}₽</b>"

    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Очистить", callback_data="clear_cart")
    builder.button(text="✅ Оформить", callback_data="create_order")
    builder.button(text="🛍 В каталог", callback_data="back_to_products")
    builder.button(text="🏠 Главная", callback_data="main_menu")
    builder.adjust(2)

    if hasattr(message, 'edit_text'):
        await message.edit_text(cart_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message.answer(cart_text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.message(Command("cart"))
async def cmd_cart(message: types.Message):
    await show_cart_handler(message)


@router.callback_query(lambda c: c.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_carts[user_id] = []

    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 В каталог", callback_data="back_to_products")
    builder.button(text="🏠 Главная", callback_data="main_menu")
    builder.adjust(1)

    await callback.message.edit_text(
        "🗑 <b>Корзина очищена!</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer("Корзина очищена!")


@router.callback_query(lambda c: c.data == "create_order")
async def create_order(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    total = sum(item['price'] for item in cart)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_order")
    builder.button(text="🔙 Назад", callback_data="cart")
    builder.adjust(1)

    await callback.message.edit_text(
        f"✅ <b>Оформление заказа</b>\n\n"
        f"Товаров: {len(cart)}\n"
        f"Сумма: {total}₽\n\n"
        f"Для оформления нажмите 'Подтвердить'.\n"
        f"Администратор свяжется с вами в ближайшее время.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "confirm_order")
async def confirm_order(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    total = sum(item['price'] for item in cart)

    # Очищаем корзину
    user_carts[user_id] = []

    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 В каталог", callback_data="back_to_products")
    builder.button(text="🏠 Главная", callback_data="main_menu")
    builder.adjust(1)

    await callback.message.edit_text(
        f"🎉 <b>Заказ оформлен!</b>\n\n"
        f"Номер заказа: #{user_id}{len(cart)}\n"
        f"Сумма: {total}₽\n"
        f"Товаров: {len(cart)}\n\n"
        f"Администратор свяжется с вами для уточнения деталей.\n"
        f"Спасибо за покупку! 🛍",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer("Заказ оформлен! Администратор свяжется с вами.", show_alert=True)