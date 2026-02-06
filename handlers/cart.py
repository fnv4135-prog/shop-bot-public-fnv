from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

# Временная корзина в памяти
user_carts = {}


@router.message(Command("cart"))
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await message.answer("🛒 Ваша корзина пуста")
        return

    total = sum(item["price"] * item["quantity"] for item in cart)
    cart_text = "\n".join([
        f"{item['name']} × {item['quantity']} = {item['price'] * item['quantity']}₽"
        for item in cart
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")]
    ])

    await message.answer(
        f"🛒 **Ваша корзина:**\n\n{cart_text}\n\n"
        f"💰 **Итого: {total}₽**",
        reply_markup=keyboard
    )


@router.callback_query(lambda c: c.data.startswith("add_"))
async def add_to_cart(callback: types.CallbackQuery):
    from handlers.products import products

    user_id = callback.from_user.id
    product_id = int(callback.data.split("_")[1])
    product = next((p for p in products if p["id"] == product_id), None)

    if not product:
        await callback.answer("Товар не найден")
        return

    if user_id not in user_carts:
        user_carts[user_id] = []

    # Ищем товар в корзине
    cart_item = next((item for item in user_carts[user_id] if item["id"] == product_id), None)

    if cart_item:
        cart_item["quantity"] += 1
    else:
        user_carts[user_id].append({
            "id": product_id,
            "name": product["name"],
            "price": product["price"],
            "quantity": 1
        })

    await callback.answer(f"{product['name']} добавлен в корзину!")


@router.callback_query(lambda c: c.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in user_carts:
        user_carts[user_id] = []
    await callback.message.edit_text("🗑 Корзина очищена")
    await callback.answer()


@router.callback_query(lambda c: c.data == "cart")
async def show_cart_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await callback.message.answer("🛒 Ваша корзина пуста")
        return

    total = sum(item["price"] * item["quantity"] for item in cart)
    cart_text = "\n".join([
        f"{item['name']} × {item['quantity']} = {item['price'] * item['quantity']}₽"
        for item in cart
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")]
    ])

    await callback.message.answer(
        f"🛒 **Ваша корзина:**\n\n{cart_text}\n\n"
        f"💰 **Итого: {total}₽**",
        reply_markup=keyboard
    )
    await callback.answer()