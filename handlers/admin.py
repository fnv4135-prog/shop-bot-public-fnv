from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

# Исправленный импорт - все из database
from database import get_all_products, count_products, count_carts, add_product

# Константы для callback_data
CALLBACK_CATEGORIES = "admin_categories"
CALLBACK_CATEGORY_ADD = "admin_category_add"
CALLBACK_CATEGORY_EDIT = "admin_category_edit_"
CALLBACK_CATEGORY_DELETE = "admin_category_del_"
CALLBACK_CATEGORY_BACK = "admin_categories_back"
CALLBACK_CATEGORY_ADD_CANCEL = "admin_category_add_cancel"

class AddCategory(StatesGroup):
    waiting_for_name = State()
    waiting_for_parent = State()
    waiting_for_sort = State()
    waiting_for_active = State()

router = Router()
logger = logging.getLogger(__name__)

# === НАСТРОЙКА ПРАВ ДОСТУПА ===
ADMIN_IDS = {524082641}  # Ваш ID


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


# === FSM ДЛЯ ДОБАВЛЕНИЯ ТОВАРА ===
class AddProduct(StatesGroup):
    """Состояния для добавления нового товара"""
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_category = State()


# === КОМАНДА /admin ДЛЯ ВЫЗОВА АДМИНКИ ===
@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Основная команда админ-панели"""
    if not is_admin(message.from_user.id):
        logger.warning(f"⚠️ Неавторизованный доступ к админке от {message.from_user.id}")
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return

    # Получаем статистику из БД
    try:
        products_count = await count_products()
        carts_count = await count_carts()  # Теперь функция есть!
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        products_count = "ошибка"
        carts_count = "ошибка"

    # Клавиатура админ-меню
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
        [types.InlineKeyboardButton(text="📝 Управление товарами", callback_data="admin_manage_products")],
        [types.InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [types.InlineKeyboardButton(text="📂 Управление категориями", callback_data=CALLBACK_CATEGORIES)],
        [types.InlineKeyboardButton(text="🏠 В главное меню", callback_data="go_home")]
    ])

    await message.answer(
        f"🛠️ <b>Админ-панель магазина</b>\n\n"
        f"📦 Товаров в БД: {products_count}\n"
        f"🛒 Активных корзин: {carts_count}\n\n"
        f"Выберите действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"👑 Админ {message.from_user.id} открыл админ-панель")


# === НАЧАЛО ДОБАВЛЕНИЯ ТОВАРА ===
@router.callback_query(F.data == "admin_add_product")
async def start_add_product(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса добавления товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return

    await state.set_state(AddProduct.waiting_for_name)

    await callback.message.edit_text(
        "➕ <b>Добавление нового товара</b>\n\n"
        "Введите <b>название товара</b>:\n\n"
        "<i>Пример: 📱 iPhone 15 Pro Max</i>",
        parse_mode="HTML"
    )
    await callback.answer()


# === ОБРАБОТКА НАЗВАНИЯ ===
@router.message(AddProduct.waiting_for_name)
async def process_product_name(message: types.Message, state: FSMContext):
    """Получаем название товара и запрашиваем описание"""
    await state.update_data(name=message.text)
    await state.set_state(AddProduct.waiting_for_description)

    await message.answer(
        "✅ Название сохранено!\n\n"
        "Теперь введите <b>описание товара</b>:\n\n"
        "<i>Пример: Новый флагман Apple с камерой 48 МП</i>",
        parse_mode="HTML"
    )


# === ОБРАБОТКА ОПИСАНИЯ ===
@router.message(AddProduct.waiting_for_description)
async def process_product_description(message: types.Message, state: FSMContext):
    """Получаем описание и запрашиваем цену"""
    await state.update_data(description=message.text)
    await state.set_state(AddProduct.waiting_for_price)

    await message.answer(
        "✅ Описание сохранено!\n\n"
        "Теперь введите <b>цену товара</b> (только число):\n\n"
        "<i>Пример: 129900 (для 129 900 ₽)</i>",
        parse_mode="HTML"
    )


# === ОБРАБОТКА ЦЕНЫ ===
@router.message(AddProduct.waiting_for_price)
async def process_product_price(message: types.Message, state: FSMContext):
    """Получаем цену и запрашиваем категорию"""
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
    except ValueError:
        await message.answer(
            "❌ Неверный формат цены!\n"
            "Введите целое положительное число:\n\n"
            "<i>Пример: 79900</i>",
            parse_mode="HTML"
        )
        return

    await state.update_data(price=price)
    await state.set_state(AddProduct.waiting_for_category)

    await message.answer(
        "✅ Цена сохранена!\n\n"
        "Теперь введите <b>категорию товара</b>:\n\n"
        "<i>Пример: Смартфоны, Ноутбуки, Аксессуары</i>",
        parse_mode="HTML"
    )


# === ОБРАБОТКА КАТЕГОРИИ И ФИНАЛИЗАЦИЯ ===
@router.message(AddProduct.waiting_for_category)
async def process_product_category(message: types.Message, state: FSMContext):
    """Получаем категорию и сохраняем товар в БД"""
    category = message.text

    # Получаем все сохранённые данные
    data = await state.get_data()
    await state.clear()

    try:
        # Добавляем товар в БД
        product_id = await add_product(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            category=category
        )

        logger.info(f"🆕 Админ добавил товар в БД: {data['name']} за {data['price']}₽, ID: {product_id}")

        # Показываем результат
        await message.answer(
            f"✅ <b>Товар успешно добавлен в базу данных!</b>\n\n"
            f"🆔 ID: {product_id}\n"
            f"📦 Название: {data['name']}\n"
            f"📝 Описание: {data['description']}\n"
            f"💰 Цена: {data['price']}₽\n"
            f"🏷️ Категория: {category}\n\n"
            f"Теперь он доступен в каталоге для всех пользователей.",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при добавлении товара в БД: {e}")
        await message.answer(
            f"❌ <b>Ошибка при добавлении товара в БД:</b>\n\n"
            f"{str(e)}\n\n"
            f"Попробуйте снова или проверьте подключение к базе данных.",
            parse_mode="HTML"
        )
        return

    # Предлагаем дальше
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ Добавить ещё товар", callback_data="admin_add_product")],
        [types.InlineKeyboardButton(text="📦 Перейти в каталог", callback_data="show_catalog")],
        [types.InlineKeyboardButton(text="🏠 В главное меню", callback_data="go_home")]
    ])

    await message.answer("Что дальше?", reply_markup=keyboard)


# === ОБРАБОТЧИК ОТМЕНЫ ===
@router.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Отмена текущего действия в админке"""
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    await callback.answer()


# === УПРАВЛЕНИЕ ТОВАРАМИ ===
@router.callback_query(F.data == "admin_manage_products")
async def manage_products(callback: types.CallbackQuery):
    """Управление товарами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return

    try:
        products = await get_all_products()

        if not products:
            await callback.message.edit_text(
                "📝 <b>Управление товарами</b>\n\n"
                "В базе данных нет товаров.\n\n"
                "Начните с добавления первого товара!",
                parse_mode="HTML"
            )
            return

        # Формируем список товаров (первые 5 для примера)
        text = "📝 <b>Управление товарами</b>\n\n"
        for product in products[:5]:  # Показываем первые 5
            text += f"🆔 <b>{product['id']}</b>: {product['name']} - {product['price']}₽\n"

        if len(products) > 5:
            text += f"\n... и ещё {len(products) - 5} товаров"

        # Клавиатура для управления
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✏️ Редактировать товар", callback_data="admin_edit_product")],
            [types.InlineKeyboardButton(text="🗑 Удалить товар", callback_data="admin_delete_product")],
            [types.InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_back")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при получении товаров: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка при загрузке товаров</b>\n\n"
            "Проверьте подключение к базе данных.",
            parse_mode="HTML"
        )

    await callback.answer()


# === СТАТИСТИКА ===
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return

    try:
        from database import get_all_products, count_carts  # и другие функции подсчёта
        from database.orders import get_all_orders_stats  # эту функцию мы создадим ниже

        products_count = await count_products()  # должно быть в database/products.py
        carts_count = await count_carts()        # должно быть в database/cart.py
        orders_stats = await get_all_orders_stats()  # создадим

        stats_text = (
            f"📊 <b>Статистика магазина</b>\n\n"
            f"📦 Товаров в каталоге: {products_count}\n"
            f"🛒 Активных корзин: {carts_count}\n"
            f"📝 Всего заказов: {orders_stats['total_orders']}\n"
            f"💰 Выручка: {orders_stats['total_revenue']}₽\n"
            f"✅ Выполнено заказов: {orders_stats['completed_orders']}\n"
            f"🆕 Новых заказов: {orders_stats['new_orders']}\n"
        )

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
            [types.InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_back")]
        ])

        await callback.message.edit_text(stats_text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await callback.message.edit_text("❌ Ошибка при загрузке статистики")

    await callback.answer()


@router.callback_query(F.data == CALLBACK_CATEGORIES)
async def admin_categories(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return

    from database.categories import get_all_categories_flat

    try:
        cats = await get_all_categories_flat(include_inactive=True)
        if not cats:
            text = "📂 Категории отсутствуют."
        else:
            text = "📂 **Список категорий:**\n\n"
            for cat in cats:
                active = "✅" if cat['is_active'] else "❌"
                text += f"{cat['path']} (id={cat['id']}) {active}\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить категорию", callback_data=CALLBACK_CATEGORY_ADD)],
            [InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_back")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        logger.exception("Ошибка при загрузке категорий")
        await callback.message.edit_text("❌ Ошибка загрузки категорий")
    await callback.answer()


@router.callback_query(F.data == CALLBACK_CATEGORY_ADD)
async def start_add_category(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return

    await state.set_state(AddCategory.waiting_for_name)
    await callback.message.edit_text(
        "➕ **Добавление новой категории**\n\n"
        "Введите название категории:",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AddCategory.waiting_for_name)
async def process_category_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    # Предложим выбрать родительскую категорию (можно пропустить)
    from database.categories import get_all_categories_flat
    cats = await get_all_categories_flat(include_inactive=True)
    kb = []
    # Добавим вариант "Корневая категория"
    kb.append([InlineKeyboardButton(text="📁 Корневая категория", callback_data="parent_none")])
    for cat in cats:
        kb.append([InlineKeyboardButton(text=cat['path'], callback_data=f"parent_{cat['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 Отмена", callback_data=CALLBACK_CATEGORY_ADD_CANCEL)])
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    await state.set_state(AddCategory.waiting_for_parent)
    await message.answer("Выберите родительскую категорию (или корневую):", reply_markup=keyboard)


@router.callback_query(AddCategory.waiting_for_parent, F.data.startswith("parent_"))
async def process_category_parent(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "parent_none":
        parent_id = None
    else:
        parent_id = int(data.split("_")[1])
    await state.update_data(parent_id=parent_id)
    await callback.message.edit_text("Введите порядок сортировки (число, чем меньше, тем выше):")
    await state.set_state(AddCategory.waiting_for_sort)
    await callback.answer()


@router.message(AddCategory.waiting_for_sort)
async def process_category_sort(message: types.Message, state: FSMContext):
    try:
        sort_order = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число!")
        return
    await state.update_data(sort_order=sort_order)
    # Спросим, активна ли категория
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="active_true"),
         InlineKeyboardButton(text="❌ Нет", callback_data="active_false")]
    ])
    await message.answer("Категория активна?", reply_markup=kb)
    await state.set_state(AddCategory.waiting_for_active)


@router.callback_query(AddCategory.waiting_for_active, F.data.in_({"active_true", "active_false"}))
async def process_category_active(callback: types.CallbackQuery, state: FSMContext):
    is_active = (callback.data == "active_true")
    data = await state.get_data()
    name = data['name']
    parent_id = data.get('parent_id')
    sort_order = data.get('sort_order', 0)

    from database.categories import create_category
    try:
        cat_id = await create_category(name, parent_id, sort_order, is_active)
        await callback.message.edit_text(f"✅ Категория '{name}' создана с ID {cat_id}.")
        # Возвращаемся к списку категорий
        await admin_categories(callback)
    except Exception as e:
        logger.exception("Ошибка создания категории")
        await callback.message.edit_text("❌ Ошибка при создании категории.")
    await state.clear()
    await callback.answer()


# Обработчик отмены
@router.callback_query(F.data == CALLBACK_CATEGORY_ADD_CANCEL)
async def cancel_add_category(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await admin_categories(callback)
    await callback.answer()


@router.message(Command("test_cats"))
async def test_categories(message: types.Message):
    """Тестовая команда для проверки структуры категорий (только для админа)"""
    if not is_admin(message.from_user.id):
        return

    from database.categories import get_category_tree

    try:
        tree = await get_category_tree(include_inactive=True)
        # Превращаем дерево в читаемый текст
        result = "🌳 **Дерево категорий:**\n\n"

        def format_tree(cats, level=0):
            text = ""
            for cat in cats:
                prefix = "  " * level + "• "
                text += f"{prefix}{cat['name']} (id={cat['id']}, active={cat['is_active']})\n"
                if cat.get('children'):
                    text += format_tree(cat['children'], level + 1)
            return text

        result += format_tree(tree)
        await message.answer(result, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        logger.exception("Ошибка в test_categories")

# === ВОЗВРАТ В АДМИНКУ ===
@router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    """Возврат в главное меню админки"""
    await cmd_admin(callback.message)
    await callback.answer()