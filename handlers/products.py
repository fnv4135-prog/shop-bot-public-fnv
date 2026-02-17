"""
handlers/products.py - Иерархический каталог товаров с категориями
"""
import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_products_by_category, add_to_cart, get_product_by_id
from database.categories import get_category_tree, get_category_children, get_category_name

router = Router()
logger = logging.getLogger(__name__)


async def get_products_keyboard(category_id: int):
    """Возвращает клавиатуру со списком товаров в категории и текст"""
    products = await get_products_by_category(category_id, include_inactive=False)
    if not products:
        return None, "🛒 В этой категории пока нет товаров"
    kb = []
    for p in products:
        kb.append([InlineKeyboardButton(
            text=f"{p['name']} - {p['price']}₽",
            callback_data=f"product_{p['id']}"
        )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"cat_{category_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb), f"🛒 Товары в категории:"


async def get_category_keyboard(category_id: int = None):
    """
    Возвращает клавиатуру для отображения подкатегорий или товаров.
    Возвращает кортеж (keyboard, text) или (None, error_text) в случае ошибки.
    """
    if category_id is None:
        # Корневые категории
        categories = await get_category_tree(parent_id=None, include_inactive=False)
        if not categories:
            return None, "📭 Каталог временно пуст"
        kb = []
        for cat in categories:
            kb.append([InlineKeyboardButton(
                text=f"📁 {cat['name']}",
                callback_data=f"cat_{cat['id']}"
            )])
        kb.append([InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")])
        return InlineKeyboardMarkup(inline_keyboard=kb), "📁 Выберите категорию:"

    else:
        # Получаем подкатегории
        subcats = await get_category_children(category_id, include_inactive=False)
        cat_name = await get_category_name(category_id) or "Категория"

        if subcats:
            # Есть подкатегории – показываем их
            kb = []
            for sub in subcats:
                kb.append([InlineKeyboardButton(
                    text=f"📂 {sub['name']}",
                    callback_data=f"cat_{sub['id']}"
                )])
            kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="show_catalog")])
            return InlineKeyboardMarkup(inline_keyboard=kb), f"📁 {cat_name}:"
        else:
            # Нет подкатегорий – сразу показываем товары
            return await get_products_keyboard(category_id)


@router.message(Command("products"))
async def cmd_products(message: types.Message):
    """Команда /products - показать каталог"""
    await show_catalog(message)


@router.callback_query(lambda c: c.data == "show_catalog")
async def show_catalog_callback(callback: types.CallbackQuery):
    """Обработчик кнопки 'Каталог'"""
    await show_catalog(callback.message)
    await callback.answer()


async def show_catalog(message: types.Message):
    """Показать корневые категории"""
    keyboard, text = await get_category_keyboard()
    if keyboard:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text)


@router.callback_query(lambda c: c.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery):
    """Обработчик выбора категории или перехода к товарам"""
    data = callback.data.split("_")

    if len(data) == 2:  # просто выбор категории
        cat_id = int(data[1])
        keyboard, text = await get_category_keyboard(cat_id)
        if keyboard:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.message.edit_text(text)

    elif len(data) == 3 and data[1] == "products":  # просмотр товаров в категории
        cat_id = int(data[2])
        keyboard, text = await get_products_keyboard(cat_id)
        if keyboard:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.message.edit_text(text)

    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("product_"))
async def show_product_detail(callback: types.CallbackQuery):
    """Показать детали товара и кнопку добавления в корзину"""
    product_id = int(callback.data.split("_")[1])
    logger.info(f"🔍 show_product_detail вызван с data={callback.data}")

    product = await get_product_by_id(product_id)

    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    # Создаём клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить в корзину",
                                 callback_data=f"add_to_cart_{product_id}"),
            InlineKeyboardButton(text="🛒 В корзину",
                                 callback_data="view_cart")
        ],
        [InlineKeyboardButton(text="🔙 Назад к товарам",
                              callback_data=f"cat_products_{product['category_id']}")]
    ])

    description = product.get('description', "Описание отсутствует")
    await callback.message.edit_text(
        f"📱 <b>{product['name']}</b>\n\n"
        f"📝 <b>Описание:</b> {description}\n"
        f"💰 <b>Цена:</b> {product['price']} руб.\n\n"
        f"🛒 <i>Добавьте товар в корзину:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("add_to_cart_"))
async def add_to_cart_handler(callback: types.CallbackQuery):
    """Добавление товара в корзину"""
    product_id = int(callback.data.split("_")[3])

    try:
        await add_to_cart(callback.from_user.id, product_id, 1)

        product = await get_product_by_id(product_id)
        product_name = product['name'] if product else f"Товар {product_id}"

        from utils import gsheets
        import asyncio
        asyncio.create_task(gsheets.log_add_to_cart(
            user_id=callback.from_user.id,
            username=callback.from_user.username or "",
            product_id=product_id,
            product_name=product_name
        ))

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

    except Exception as e:
        logger.error(f"Ошибка добавления в корзину: {e}")
        await callback.answer("❌ Ошибка при добавлении в корзину", show_alert=True)