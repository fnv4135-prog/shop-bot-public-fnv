"""
handlers/products.py - Иерархический каталог товаров с категориями
"""
import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_products_by_category, add_to_cart
from database.categories import get_category_tree, get_category_children, get_category_name

router = Router()
logger = logging.getLogger(__name__)


async def get_category_keyboard(category_id: int = None):
    """
    Строит клавиатуру для отображения подкатегорий или товаров.
    Если category_id = None, показываем корневые категории.
    Если у категории есть подкатегории, показываем их (товары не показываем).
    Если подкатегорий нет, сразу показываем товары (вызываем get_products_keyboard).
    """
    if category_id is None:
        # Корневые категории
        categories = await get_category_tree(parent_id=None, include_inactive=False)
        if not categories:
            return None, "📭 Каталог временно пуст", None
        kb = []
        for cat in categories:
            kb.append([InlineKeyboardButton(
                text=f"📁 {cat['name']}",
                callback_data=f"cat_{cat['id']}"
            )])
        kb.append([InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")])
        return InlineKeyboardMarkup(inline_keyboard=kb), "📁 Выберите категорию:", None

    else:
        # Получаем подкатегории
        subcats = await get_category_children(category_id, include_inactive=False)

        if subcats:
            # Есть подкатегории – показываем только их
            kb = []
            for sub in subcats:
                kb.append([InlineKeyboardButton(
                    text=f"📂 {sub['name']}",
                    callback_data=f"cat_{sub['id']}"
                )])
            kb.append([InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="show_catalog"
            )])
            cat_name = await get_category_name(category_id)
            return InlineKeyboardMarkup(inline_keyboard=kb), f"📁 {cat_name}:", None
        else:
            # Нет подкатегорий – сразу показываем товары
            return await get_products_keyboard(category_id)


async def get_products_keyboard(category_id: int):
    """Показывает список товаров в категории"""
    products = await get_products_by_category(category_id, include_inactive=False)
    if not products:
        return None, "🛒 В этой категории пока нет товаров"

    kb = []
    for p in products:
        kb.append([InlineKeyboardButton(
            text=f"{p['name']} - {p['price']}₽",
            callback_data=f"product_{p['id']}"
        )])

    # Кнопка назад к подкатегориям
    kb.append([InlineKeyboardButton(
        text="🔙 Назад",
        callback_data=f"cat_{category_id}"
    )])

    return InlineKeyboardMarkup(inline_keyboard=kb), f"🛒 Товары в категории:"


@router.message(Command("products"))
async def cmd_products(message: types.Message):
    """Команда /products - показать каталог"""
    await show_catalog(message)


@router.callback_query(lambda c: c.data == "show_catalog")
async def show_catalog(callback: types.CallbackQuery):
    """Обработчик кнопки 'Каталог'"""
    await callback.message.delete()  # удаляем старое сообщение, чтобы не копились
    await show_catalog(callback.message)
    await callback.answer()


async def show_catalog(message: types.Message):
    """Показать корневые категории"""
    keyboard, text, _ = await get_category_keyboard()  # игнорируем третий элемент
    if keyboard:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text)


@router.callback_query(lambda c: c.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery):
    """Обработчик выбора категории"""
    cat_id = int(callback.data.split("_")[1])
    result = await get_category_keyboard(cat_id)
    if result[0] is None:
        # Это сообщение об ошибке или пустоте
        await callback.message.edit_text(result[1])
    else:
        keyboard, text = result[0], result[1]
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("product_"))
async def show_product_detail(callback: types.CallbackQuery):
    """Показать детали товара и кнопку добавления в корзину"""
    product_id = int(callback.data.split("_")[1])

    from database import get_product_by_id
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

        # Получаем название товара для лога
        from database import get_product_by_id
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