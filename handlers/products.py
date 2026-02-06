from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

# Тестовые товары
products = [
    {"id": 1, "name": "📱 iPhone 15", "price": 79900, "description": "Новый iPhone 15"},
    {"id": 2, "name": "💻 MacBook Air", "price": 119900, "description": "Ноутбук Apple"},
    {"id": 3, "name": "🎧 AirPods Pro", "price": 24900, "description": "Беспроводные наушники"},
]


@router.message(Command("products"))
async def show_products(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                                        [InlineKeyboardButton(text=f"{p['name']} - {p['price']}₽",
                                                                              callback_data=f"product_{p['id']}")]
                                                        for p in products
                                                    ] + [
                                                        [InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")]])

    await message.answer("🏪 **Каталог товаров:**\nВыберите товар:", reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith("product_"))
async def show_product_detail(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = next((p for p in products if p["id"] == product_id), None)

    if product:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Добавить в корзину", callback_data=f"add_{product_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_products")]
        ])

        await callback.message.edit_text(
            f"**{product['name']}**\n\n"
            f"{product['description']}\n\n"
            f"💰 Цена: {product['price']}₽",
            reply_markup=keyboard
        )

    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_products")
async def back_to_products(callback: types.CallbackQuery):
    await show_products(callback.message)