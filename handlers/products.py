from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging

router = Router()
logger = logging.getLogger(__name__)

# Товары
products = [
    {"id": 1, "name": "📱 iPhone 15", "price": 79900, "description": "Новый iPhone 15"},
    {"id": 2, "name": "💻 MacBook Air", "price": 119900, "description": "Ноутбук Apple"},
    {"id": 3, "name": "🎧 AirPods Pro", "price": 24900, "description": "Беспроводные наушники"},
]

# Временная корзина
user_carts = {}


@router.message(Command("products"))
async def show_products(message: types.Message):
    """Показать каталог товаров"""
    logger.info(f"📦 Пользователь {message.from_user.id} запросил каталог")

    # Создаем кнопки для каждого товара
    keyboard_buttons = []

    for product in products:
        button = InlineKeyboardButton(
            text=f"{product['name']} - {product['price']}₽",
            callback_data=f"product_{product['id']}"
        )
        keyboard_buttons.append([button])

    # Кнопки навигации
    keyboard_buttons.append([
        InlineKeyboardButton(text="🛒 Корзина", callback_data="view_cart"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(
        "🏪 <b>Каталог товаров:</b>\n\nВыберите товар:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(lambda c: c.data.startswith("product_"))
async def show_product_detail(callback: types.CallbackQuery):
    """Показать детали товара"""
    logger.info(f"🛍️ ВЫЗВАН обработчик show_product_detail с данными: {callback.data}")

    try:
        product_id = int(callback.data.split("_")[1])
        logger.info(f"🆔 ID товара: {product_id}")

        product = next((p for p in products if p["id"] == product_id), None)

        if not product:
            logger.error(f"❌ Товар с id {product_id} не найден")
            await callback.answer("Товар не найден", show_alert=True)
            return

        logger.info(f"✅ Найден товар: {product['name']}")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Добавить в корзину",
                                  callback_data=f"add_{product_id}")],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_products"),
                InlineKeyboardButton(text="🛒 Корзина", callback_data="view_cart")
            ]
        ])

        logger.info(f"📝 Редактирую сообщение для пользователя {callback.from_user.id}")

        await callback.message.edit_text(
            f"<b>{product['name']}</b>\n\n"
            f"{product['description']}\n\n"
            f"💰 Цена: <b>{product['price']}₽</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        logger.info(f"✅ Сообщение отредактировано для товара {product_id}")

        await callback.answer()

    except Exception as e:
        logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА в show_product_detail: {e}", exc_info=True)
        await callback.answer("Ошибка при загрузке товара", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("add_"))
async def add_to_cart(callback: types.CallbackQuery):
    """Добавить товар в корзину"""
    logger.info(f"🛒 ВЫЗВАН обработчик add_to_cart с данными: {callback.data}")

    try:
        product_id = int(callback.data.split("_")[1])
        product = next((p for p in products if p["id"] == product_id), None)

        if not product:
            logger.error(f"❌ Товар с id {product_id} не найден при добавлении в корзину")
            await callback.answer("Товар не найден", show_alert=True)
            return

        user_id = callback.from_user.id
        logger.info(f"👤 Добавляем товар для пользователя {user_id}")

        # Инициализируем корзину
        if user_id not in user_carts:
            user_carts[user_id] = []
            logger.info(f"🆕 Создана новая корзина для пользователя {user_id}")

        # Добавляем товар
        user_carts[user_id].append(product)

        # Подсчет
        cart_count = len(user_carts[user_id])
        total_price = sum(item['price'] for item in user_carts[user_id])

        logger.info(f"✅ Товар добавлен. В корзине: {cart_count} товаров на {total_price}₽")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Перейти в корзину", callback_data="view_cart")],
            [InlineKeyboardButton(text="🔙 Продолжить покупки", callback_data="back_to_products")]
        ])

        await callback.message.edit_text(
            f"✅ <b>{product['name']}</b> добавлен в корзину!\n\n"
            f"💰 Цена: {product['price']}₽\n"
            f"🛍 В корзине: {cart_count} товар(ов) на {total_price}₽",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        await callback.answer("Товар добавлен!")

    except Exception as e:
        logger.error(f"❌ Ошибка в add_to_cart: {e}", exc_info=True)
        await callback.answer("Ошибка при добавлении в корзину", show_alert=True)


@router.callback_query(lambda c: c.data == "back_to_products")
async def back_to_products(callback: types.CallbackQuery):
    """Вернуться к каталогу"""
    logger.info(f"🔙 Возврат в каталог от пользователя {callback.from_user.id}")
    await show_products(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data == "go_home")
async def go_home(callback: types.CallbackQuery):
    """На главную"""
    logger.info(f"🏠 Переход на главную от пользователя {callback.from_user.id}")
    await callback.message.edit_text(
        "🏪 <b>Добро пожаловать в магазин!</b>\n\n"
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/products - Показать каталог\n"
        "/cart - Корзина\n"
        "/order - Оформление заказа\n"
        "/help - Помощь",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "view_cart")
async def view_cart(callback: types.CallbackQuery):
    """Показать корзину"""
    logger.info(f"🛒 Показ корзины для пользователя {callback.from_user.id}")
    from handlers.cart import show_cart_handler
    await show_cart_handler(callback.message, callback.from_user.id)
    await callback.answer()