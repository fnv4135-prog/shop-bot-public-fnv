from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

# Товары
products = [
    {"id": 1, "name": "📱 iPhone 15", "price": 79900, "description": "Новый iPhone 15"},
    {"id": 2, "name": "💻 MacBook Air", "price": 119900, "description": "Ноутбук Apple"},
    {"id": 3, "name": "🎧 AirPods Pro", "price": 24900, "description": "Беспроводные наушники"},
]

# Временная корзина в памяти
user_carts = {}


@router.message(Command("products"))
async def show_products(message: types.Message):
    # Создаём клавиатуру
    builder = InlineKeyboardBuilder()

    for product in products:
        builder.button(
            text=f"{product['name']} - {product['price']}₽",
            callback_data=f"product_{product['id']}"
        )

    builder.button(text="🛒 Корзина", callback_data="cart")
    builder.button(text="🏠 Главная", callback_data="main_menu")

    builder.adjust(1)  # По одному в ряд

    await message.answer(
        "🏪 <b>Каталог товаров:</b>\nВыберите товар:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(lambda c: c.data.startswith("product_"))
async def process_product(callback: types.CallbackQuery):
    try:
        product_id = int(callback.data.split("_")[1])
        product = next((p for p in products if p["id"] == product_id), None)

        if product:
            # Клавиатура для товара
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Добавить в корзину", callback_data=f"add_{product_id}")
            builder.button(text="🔙 Назад", callback_data="back_to_products")
            builder.button(text="🛒 Корзина", callback_data="cart")
            builder.adjust(1)

            await callback.message.edit_text(
                f"<b>{product['name']}</b>\n\n"
                f"{product['description']}\n\n"
                f"💰 Цена: <b>{product['price']}₽</b>",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )

        await callback.answer()
    except Exception as e:
        print(f"Ошибка в process_product: {e}")
        await callback.answer("Произошла ошибка")


@router.callback_query(lambda c: c.data.startswith("add_"))
async def add_to_cart(callback: types.CallbackQuery):
    try:
        product_id = int(callback.data.split("_")[1])
        product = next((p for p in products if p["id"] == product_id), None)

        if product:
            user_id = callback.from_user.id

            # Инициализируем корзину
            if user_id not in user_carts:
                user_carts[user_id] = []

            # Добавляем товар
            user_carts[user_id].append(product)

            # Считаем
            cart_count = len(user_carts[user_id])
            total = sum(item['price'] for item in user_carts[user_id])

            builder = InlineKeyboardBuilder()
            builder.button(text="🛒 Перейти в корзину", callback_data="cart")
            builder.button(text="🔙 Продолжить покупки", callback_data="back_to_products")
            builder.adjust(1)

            await callback.message.edit_text(
                f"✅ <b>{product['name']}</b> добавлен в корзину!\n\n"
                f"💰 Цена: {product['price']}₽\n"
                f"🛍 В корзине: {cart_count} товар(ов) на {total}₽",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )

        await callback.answer("Товар добавлен!")
    except Exception as e:
        print(f"Ошибка в add_to_cart: {e}")
        await callback.answer("Ошибка при добавлении")


@router.callback_query(lambda c: c.data == "back_to_products")
async def back_to_products(callback: types.CallbackQuery):
    # Просто показываем продукты снова
    builder = InlineKeyboardBuilder()

    for product in products:
        builder.button(
            text=f"{product['name']} - {product['price']}₽",
            callback_data=f"product_{product['id']}"
        )

    builder.button(text="🛒 Корзина", callback_data="cart")
    builder.button(text="🏠 Главная", callback_data="main_menu")
    builder.adjust(1)

    await callback.message.edit_text(
        "🏪 <b>Каталог товаров:</b>\nВыберите товар:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 Каталог", callback_data="back_to_products")
    builder.button(text="🛒 Корзина", callback_data="cart")
    builder.button(text="❓ Помощь", callback_data="help")
    builder.adjust(1)

    await callback.message.edit_text(
        "🏪 <b>Добро пожаловать в магазин!</b>\n\n"
        "Выберите действие:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "cart")
async def show_cart(callback: types.CallbackQuery):
    from handlers.cart import show_cart_handler
    await show_cart_handler(callback.message, callback.from_user.id)
    await callback.answer()