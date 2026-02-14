from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging

import asyncio
from utils import gsheets

from database import get_all_products, get_product_by_id, add_to_cart

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("products"))
async def show_products(message: types.Message):
    """Показать каталог товаров из БД"""
    logger.info(f"📦 Пользователь {message.from_user.id} запросил каталог")

    # Получаем товары из БД (АСИНХРОННО!)
    products = await get_all_products()

    if not products:
        await message.answer("📭 Каталог товаров пуст")
        return

    # Создаём кнопки для каждого товара
    keyboard_buttons = []
    for product in products:
        button = InlineKeyboardButton(
            text=f"{product['name']} - {product['price']} руб.",
            callback_data=f"product_{product['id']}"
        )
        keyboard_buttons.append([button])

    # Добавляем кнопку возврата в меню
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="go_home")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(
        "🛒 <b>Каталог товаров:</b>\n\n"
        "Выберите товар для добавления в корзину:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(lambda c: c.data == "show_catalog")
async def show_catalog_callback(callback: types.CallbackQuery):
    """Показать каталог при нажатии на кнопку 'Каталог товаров'"""
    await show_products(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("product_"))
async def show_product_detail(callback: types.CallbackQuery):
    """Показать детали товара и кнопку добавления в корзину"""
    product_id = int(callback.data.split("_")[1])

    # Получаем товар из БД
    product = await get_product_by_id(product_id)

    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить в корзину",
                                 callback_data=f"add_to_cart_{product_id}"),
            InlineKeyboardButton(text="🛒 В корзину",
                                 callback_data="view_cart")
        ],
        [InlineKeyboardButton(text="⬅️ Назад к каталогу",
                              callback_data="show_catalog")]
    ])

    # Формируем описание
    description = product.get('description', "Описание отсутствует")
    category = product.get('category', 'Без категории')

    await callback.message.edit_text(
        f"📱 <b>{product['name']}</b>\n\n"
        f"📝 <b>Описание:</b> {description}\n"
        f"💰 <b>Цена:</b> {product['price']} руб.\n"
        f"📦 <b>Категория:</b> {category}\n\n"
        f"🛒 <i>Добавьте товар в корзину:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("add_to_cart_"))
async def add_to_cart_handler(callback: types.CallbackQuery):
    """Обработчик добавления товара в корзину"""
    product_id = int(callback.data.split("_")[3])

    try:
        # Используем функцию из database.cart
        await add_to_cart(callback.from_user.id, product_id, 1)

        # Кнопки для продолжения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Перейти в корзину",
                                     callback_data="view_cart"),
                InlineKeyboardButton(text="📦 Продолжить покупки",
                                     callback_data="show_catalog")
            ]
        ])

        await callback.message.edit_text(
            "✅ <b>Товар успешно добавлен в корзину!</b>\n\n"
            "Что вы хотите сделать дальше?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer("Товар добавлен в корзину!")

        from database import get_product_by_id  # если ещё не импортирован

        product_info = await get_product_by_id(product_id)
        product_name = product_info['name'] if product_info else f"Товар {product_id}"

        asyncio.create_task(gsheets.log_add_to_cart(
            user_id=callback.from_user.id,
            username=callback.from_user.username or "",
            product_id=product_id,
            product_name=product_name
        ))

    except Exception as e:
        logger.error(f"Ошибка добавления в корзину: {e}")
        await callback.answer("❌ Ошибка при добавлении в корзину", show_alert=True)