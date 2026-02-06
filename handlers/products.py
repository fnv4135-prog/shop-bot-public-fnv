from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

# Тестовые товары
products = [
    {"id": 1, "name": "📱 iPhone 15", "price": 79900, "description": "Новый iPhone 15"},
    {"id": 2, "name": "💻 MacBook Air", "price": 119900, "description": "Ноутбук Apple"},
    {"id": 3, "name": "🎧 AirPods Pro", "price": 24900, "description": "Беспроводные наушники"},
]

# Временное хранилище корзины (в реальном проекте используйте базу данных)
user_carts = {}


@router.message(Command("products"))
async def show_products(message: types.Message):
    # Создаем клавиатуру с товарами
    keyboard_buttons = []

    for product in products:
        button = InlineKeyboardButton(
            text=f"{product['name']} - {product['price']}₽",
            callback_data=f"view_product_{product['id']}"
        )
        keyboard_buttons.append([button])

    # Добавляем кнопку корзины
    keyboard_buttons.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(
        "<b>🏪 Каталог товаров:</b>\nВыберите товар:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("view_product_"))
async def show_product_detail(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    product = next((p for p in products if p["id"] == product_id), None)

    if product:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Добавить в корзину", callback_data=f"add_to_cart_{product_id}")],
            [InlineKeyboardButton(text="🔙 Назад к каталогу", callback_data="back_to_products")]
        ])

        await callback.message.edit_text(
            f"<b>{product['name']}</b>\n\n"
            f"{product['description']}\n\n"
            f"💰 Цена: <b>{product['price']}₽</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[3])
    product = next((p for p in products if p["id"] == product_id), None)

    if product:
        user_id = callback.from_user.id

        # Инициализируем корзину пользователя, если её нет
        if user_id not in user_carts:
            user_carts[user_id] = []

        # Добавляем товар в корзину
        user_carts[user_id].append(product)

        # Подсчитываем количество товаров в корзине
        cart_count = len(user_carts[user_id])

        # Создаем клавиатуру с обновленной информацией
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Перейти в корзину", callback_data="show_cart")],
            [InlineKeyboardButton(text="🔙 Назад к каталогу", callback_data="back_to_products")]
        ])

        await callback.message.edit_text(
            f"✅ <b>{product['name']}</b> добавлен в корзину!\n\n"
            f"💰 Цена: <b>{product['price']}₽</b>\n"
            f"🛍 В корзине: <b>{cart_count}</b> товар(ов)",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    await callback.answer(f"Товар добавлен в корзину!", show_alert=False)


@router.callback_query(F.data == "back_to_products")
async def back_to_products(callback: types.CallbackQuery):
    # Создаем клавиатуру с товарами
    keyboard_buttons = []

    for product in products:
        button = InlineKeyboardButton(
            text=f"{product['name']} - {product['price']}₽",
            callback_data=f"view_product_{product['id']}"
        )
        keyboard_buttons.append([button])

    # Добавляем кнопку корзины
    keyboard_buttons.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(
        "<b>🏪 Каталог товаров:</b>\nВыберите товар:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "show_cart")
async def show_cart(callback: types.CallbackQuery):
    from handlers.cart import show_cart_handler
    await show_cart_handler(callback.message, callback.from_user.id)
    await callback.answer()