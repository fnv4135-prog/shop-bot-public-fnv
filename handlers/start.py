# handlers/start.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from aiogram import Router, types, F
from aiogram.filters import Command
from keyboards.main_menu import main_menu_keyboard

router = Router()


@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🏪 Добро пожаловать в магазин электроники!\n"
        "Выберите действие:",
        reply_markup=main_menu_keyboard()
    )


@router.message(F.text == "📦 Каталог товаров")
async def catalog_button(message: types.Message):
    # Импортируем здесь, чтобы избежать циклических импортов
    from data.products import products

    catalog_text = "📦 *Наш каталог товаров:*\n\n"

    for product_id, product in products.items():
        catalog_text += f"{product['name']}\n"
        catalog_text += f"Цена: {product['price']}₽\n"
        catalog_text += f"Остаток: {product['stock']} шт.\n"
        catalog_text += f"---\n"

    catalog_text += "\n*Выберите товар для подробностей:*"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for product_id, product in products.items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{product['name']} - {product['price']}₽",
                callback_data=f"product_{product_id}"
            )
        ])

    await message.answer(
        catalog_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


#@router.message(F.text == "🛒 Корзина")
#async def cart_button(message: types.Message):
#    await message.answer("🛒 Ваша корзина пуста\n\nДобавьте товары из каталога!")


@router.message(F.text == "📞 Контакты")
async def contacts_button(message: types.Message):
    await message.answer(
        "📞 Наши контакты:\n\n"
        "Телефон: +7 123 456-78-90\n"
        "Адрес: г. Хабаровск, ул. Примерная, 1\n"
        "Время работы: 10:00 - 20:00\n\n"
        "Telegram: @smart_tech_store"
    )