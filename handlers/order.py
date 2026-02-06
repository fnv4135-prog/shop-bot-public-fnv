from aiogram import Router, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()


class OrderStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_address = State()


@router.callback_query(lambda c: c.data == "checkout")
async def start_checkout(callback: types.CallbackQuery, state: FSMContext):
    from handlers.cart import user_carts

    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await callback.answer("Корзина пуста")
        return

    total = sum(item["price"] * item["quantity"] for item in cart)

    await state.update_data(cart=cart, total=total)
    await state.set_state(OrderStates.waiting_for_phone)

    await callback.message.edit_text(
        "📞 **Оформление заказа**\n\n"
        f"Сумма заказа: {total}₽\n\n"
        "Пожалуйста, отправьте ваш номер телефона:"
    )
    await callback.answer()


@router.message(OrderStates.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.text
    await state.update_data(phone=phone)
    await state.set_state(OrderStates.waiting_for_address)

    await message.answer("📦 Теперь отправьте ваш адрес доставки:")


@router.message(OrderStates.waiting_for_address)
async def get_address(message: types.Message, state: FSMContext):
    address = message.text
    await state.update_data(address=address)

    data = await state.get_data()
    cart = data["cart"]
    total = data["total"]

    cart_text = "\n".join([
        f"{item['name']} × {item['quantity']} = {item['price'] * item['quantity']}₽"
        for item in cart
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")]
    ])

    await message.answer(
        f"📋 **Проверьте заказ:**\n\n"
        f"{cart_text}\n\n"
        f"💰 Итого: {total}₽\n"
        f"📞 Телефон: {data['phone']}\n"
        f"📦 Адрес: {address}\n\n"
        f"Всё верно?",
        reply_markup=keyboard
    )


@router.callback_query(lambda c: c.data == "confirm_order")
async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Здесь можно отправить уведомление владельцу
    # или сохранить заказ в базу данных

    await callback.message.edit_text(
        "✅ **Заказ оформлен!**\n\n"
        f"Номер заказа: #{callback.id}\n"
        f"Сумма: {data['total']}₽\n\n"
        "Мы свяжемся с вами для подтверждения заказа."
    )

    # Очищаем корзину
    from handlers.cart import user_carts
    user_id = callback.from_user.id
    if user_id in user_carts:
        user_carts[user_id] = []

    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel_order")
async def cancel_order(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Заказ отменен")
    await callback.answer()