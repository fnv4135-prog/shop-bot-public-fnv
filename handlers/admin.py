import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
from database import get_all_products, count_products, count_carts, add_product
from database.categories import (get_all_categories_flat, has_products, has_subcategories,
                                 create_category, update_category, delete_category)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Константы для callback_data
CALLBACK_CATEGORIES = "admin_categories"
CALLBACK_CATEGORY_ADD = "admin_category_add"
CALLBACK_CATEGORY_EDIT = "admin_category_edit_"
CALLBACK_CATEGORY_DELETE = "admin_category_del_"
CALLBACK_CATEGORY_BACK = "admin_categories_back"
CALLBACK_CATEGORY_ADD_CANCEL = "admin_category_add_cancel"
CALLBACK_CAT_DETAIL = "admin_cat_detail_"
CALLBACK_CAT_EDIT = "admin_cat_edit_"
CALLBACK_CAT_DELETE = "admin_cat_delete_"
CALLBACK_CAT_DELETE_CONFIRM = "admin_cat_delete_confirm_"
CALLBACK_CAT_EDIT_NAME = "admin_cat_edit_name"
CALLBACK_CAT_EDIT_SORT = "admin_cat_edit_sort"
CALLBACK_CAT_EDIT_ACTIVE = "admin_cat_edit_active"
CALLBACK_CAT_EDIT_PARENT = "admin_cat_edit_parent"
CALLBACK_CAT_EDIT_BACK = "admin_cat_edit_back"
CALLBACK_CAT_EDIT_SAVE = "admin_cat_edit_save"
CALLBACK_PROMO = "admin_promo"
CALLBACK_PROMO_ADD = "admin_promo_add"
CALLBACK_PROMO_LIST = "admin_promo_list"
CALLBACK_PROMO_DELETE = "admin_promo_delete_"
CALLBACK_PROMO_TOGGLE = "admin_promo_toggle_"
CALLBACK_PROMO_BACK = "admin_promo_back"

class AddCategory(StatesGroup):
    waiting_for_name = State()
    waiting_for_parent = State()
    waiting_for_sort = State()
    waiting_for_active = State()

class EditCategory(StatesGroup):
    choosing_field = State()
    waiting_for_name = State()
    waiting_for_sort = State()
    waiting_for_parent = State()
    waiting_for_active = State()

class AddPromo(StatesGroup):
    waiting_for_code = State()
    waiting_for_type = State()
    waiting_for_value = State()
    waiting_for_valid_until = State()
    waiting_for_max_uses = State()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirm = State()

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
        [types.InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [types.InlineKeyboardButton(text="🎫 Управление промокодами", callback_data=CALLBACK_PROMO)],
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
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить категорию", callback_data=CALLBACK_CATEGORY_ADD)],
                [InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_back")]
            ])
        else:
            text = "📂 **Список категорий:**\n\n"
            kb_buttons = []
            for cat in cats:
                # Показываем название и ID
                active = "✅" if cat['is_active'] else "❌"
                # Делаем категорию кликабельной
                kb_buttons.append([InlineKeyboardButton(
                    text=f"{cat['name']} (id={cat['id']}) {active}",
                    callback_data=f"{CALLBACK_CAT_DETAIL}{cat['id']}"
                )])
            # Добавляем кнопку добавления и возврата
            kb_buttons.append([InlineKeyboardButton(text="➕ Добавить категорию", callback_data=CALLBACK_CATEGORY_ADD)])
            kb_buttons.append([InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_back")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        logger.exception("Ошибка при загрузке категорий")
        await callback.message.edit_text("❌ Ошибка загрузки категорий")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith(CALLBACK_CAT_DETAIL))
async def category_detail(callback: types.CallbackQuery):
    cat_id = int(callback.data.split("_")[-1])
    from database.categories import get_all_categories_flat, has_products, has_subcategories

    try:
        # Получаем данные о категории (можно сделать отдельную функцию get_category_by_id)
        cats = await get_all_categories_flat(include_inactive=True)
        cat = next((c for c in cats if c['id'] == cat_id), None)
        if not cat:
            await callback.answer("Категория не найдена", show_alert=True)
            return

        has_products_flag = await has_products(cat_id)
        has_subs_flag = await has_subcategories(cat_id)

        text = (
            f"📁 **Категория:** {cat['name']}\n"
            f"🆔 ID: {cat['id']}\n"
            f"📊 Активна: {'✅' if cat['is_active'] else '❌'}\n"
            f"🔢 Порядок: {cat['sort_order']}\n"
            f"👆 Родитель: {cat['parent_id'] if cat['parent_id'] else 'корневая'}\n"
            f"📦 Товаров: {'есть' if has_products_flag else 'нет'}\n"
            f"📂 Подкатегорий: {'есть' if has_subs_flag else 'нет'}"
        )

        kb = [
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"{CALLBACK_CAT_EDIT}{cat_id}")],
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=CALLBACK_CATEGORIES)]
        ]
        # Кнопка удаления только если нет товаров и подкатегорий
        if not has_products_flag and not has_subs_flag:
            kb.insert(0, [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"{CALLBACK_CAT_DELETE}{cat_id}")])

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
    except Exception as e:
        logger.exception("Ошибка при загрузке деталей категории")
        await callback.answer("Ошибка", show_alert=True)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith(CALLBACK_CAT_DELETE))
async def confirm_delete_category(callback: types.CallbackQuery):
    cat_id = int(callback.data.split("_")[-1])
    # Запрашиваем подтверждение
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"{CALLBACK_CAT_DELETE_CONFIRM}{cat_id}")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"{CALLBACK_CAT_DETAIL}{cat_id}")]
    ])
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить категорию с ID {cat_id}?\n"
        "Это действие необратимо.",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith(CALLBACK_CAT_DELETE_CONFIRM))
async def delete_category(callback: types.CallbackQuery):
    cat_id = int(callback.data.split("_")[-1])
    from database.categories import delete_category
    success = await delete_category(cat_id)
    if success:
        await callback.message.edit_text("✅ Категория удалена.")
        # Возвращаемся к списку
        await asyncio.sleep(1)
        await admin_categories(callback)
    else:
        await callback.message.edit_text("❌ Не удалось удалить категорию (возможно, есть товары или подкатегории).")
        await asyncio.sleep(1)
        # Возвращаемся к деталям
        # Вызовем category_detail с новым callback
        # Можно просто вернуться в список
        await admin_categories(callback)
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


@router.callback_query(lambda c: c.data.startswith(CALLBACK_CAT_EDIT))
async def edit_category_start(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[-1])
    # Сохраняем ID в состоянии
    await state.update_data(cat_id=cat_id)
    # Показываем меню выбора поля для редактирования
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Название", callback_data=CALLBACK_CAT_EDIT_NAME)],
        [InlineKeyboardButton(text="🔢 Порядок сортировки", callback_data=CALLBACK_CAT_EDIT_SORT)],
        [InlineKeyboardButton(text="✅ Активность", callback_data=CALLBACK_CAT_EDIT_ACTIVE)],
        [InlineKeyboardButton(text="👆 Родительская категория", callback_data=CALLBACK_CAT_EDIT_PARENT)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{CALLBACK_CAT_DETAIL}{cat_id}")]
    ])
    await callback.message.edit_text("Выберите, что хотите изменить:", reply_markup=kb)
    await state.set_state(EditCategory.choosing_field)
    await callback.answer()


@router.callback_query(EditCategory.choosing_field, F.data == CALLBACK_CAT_EDIT_NAME)
async def edit_category_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новое название категории:")
    await state.set_state(EditCategory.waiting_for_name)
    await callback.answer()


@router.message(EditCategory.waiting_for_name)
async def process_edit_name(message: types.Message, state: FSMContext):
    new_name = message.text
    data = await state.get_data()
    cat_id = data['cat_id']
    from database.categories import update_category
    await update_category(cat_id, name=new_name)
    await message.answer("✅ Название обновлено.")
    # Возвращаемся к деталям (создадим новый callback)
    # Создаём новый callback-запрос для перехода к деталям
    # Лучше сбросить состояние и вернуться в админку
    await state.clear()
    # Создаём фейковый callback-запрос для вызова category_detail
    # Можно просто отправить команду вручную, но для простоты вернёмся в список
    # await admin_categories(message)  # нельзя, потому что message не callback
    # Лучше просто отправить сообщение с кнопкой "Назад"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К списку категорий", callback_data=CALLBACK_CATEGORIES)]
    ])
    await message.answer("Что дальше?", reply_markup=kb)


# Аналогично для сортировки, активности, родителя
@router.callback_query(EditCategory.choosing_field, F.data == CALLBACK_CAT_EDIT_SORT)
async def edit_category_sort(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новый порядок сортировки (целое число):")
    await state.set_state(EditCategory.waiting_for_sort)
    await callback.answer()


@router.message(EditCategory.waiting_for_sort)
async def process_edit_sort(message: types.Message, state: FSMContext):
    try:
        new_sort = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число!")
        return
    data = await state.get_data()
    cat_id = data['cat_id']
    from database.categories import update_category
    await update_category(cat_id, sort_order=new_sort)
    await message.answer("✅ Порядок сортировки обновлён.")
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К списку категорий", callback_data=CALLBACK_CATEGORIES)]
    ])
    await message.answer("Что дальше?", reply_markup=kb)


@router.callback_query(EditCategory.choosing_field, F.data == CALLBACK_CAT_EDIT_ACTIVE)
async def edit_category_active(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Активна", callback_data="active_true"),
         InlineKeyboardButton(text="❌ Неактивна", callback_data="active_false")]
    ])
    await callback.message.edit_text("Выберите статус активности:", reply_markup=kb)
    await state.set_state(EditCategory.waiting_for_active)
    await callback.answer()


@router.callback_query(EditCategory.waiting_for_active, F.data.in_({"active_true", "active_false"}))
async def process_edit_active(callback: types.CallbackQuery, state: FSMContext):
    is_active = (callback.data == "active_true")
    data = await state.get_data()
    cat_id = data['cat_id']
    from database.categories import update_category
    await update_category(cat_id, is_active=is_active)
    await callback.message.edit_text("✅ Статус активности обновлён.")
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К списку категорий", callback_data=CALLBACK_CATEGORIES)]
    ])
    await callback.message.edit_text("Что дальше?", reply_markup=kb)
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


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.message.edit_text(
        "📢 Введите текст сообщения для рассылки всем пользователям:"
    )
    await state.set_state(BroadcastStates.waiting_for_message)
    await callback.answer()


@router.message(BroadcastStates.waiting_for_message)
async def admin_broadcast_message(message: types.Message, state: FSMContext):
    text = message.text
    await state.update_data(text=text)
    # Показываем предпросмотр и запрашиваем подтверждение
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")]
    ])
    await message.answer(
        f"📢 Будет отправлено:\n\n{text}\n\nПодтвердите рассылку:",
        reply_markup=kb
    )
    await state.set_state(BroadcastStates.waiting_for_confirm)


@router.callback_query(BroadcastStates.waiting_for_confirm, F.data == "broadcast_confirm")
async def admin_broadcast_confirm(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data['text']
    await callback.message.edit_text("⏳ Начинаю рассылку...")
    await state.clear()

    # Получаем всех пользователей
    from database.users import get_all_users  # нужно создать функцию
    users = await get_all_users()
    sent = 0
    failed = 0
    for user in users:
        try:
            await callback.bot.send_message(user['telegram_id'], text)
            sent += 1
            await asyncio.sleep(0.05)  # чтобы не спамить
        except Exception as e:
            failed += 1
            logger.warning(f"Не удалось отправить пользователю {user['telegram_id']}: {e}")
    await callback.message.edit_text(f"✅ Рассылка завершена. Отправлено: {sent}, ошибок: {failed}")
    # Возвращаемся в админку
    await admin_back(callback)
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.message.edit_text(
        "📢 Введите текст сообщения для рассылки всем пользователям:"
    )
    await state.set_state(BroadcastStates.waiting_for_message)
    await callback.answer()


@router.message(BroadcastStates.waiting_for_message)
async def admin_broadcast_message(message: types.Message, state: FSMContext):
    text = message.text
    await state.update_data(text=text)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")]
    ])
    await message.answer(
        f"📢 Будет отправлено:\n\n{text}\n\nПодтвердите рассылку:",
        reply_markup=kb
    )
    await state.set_state(BroadcastStates.waiting_for_confirm)


@router.callback_query(BroadcastStates.waiting_for_confirm, F.data == "broadcast_confirm")
async def admin_broadcast_confirm(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data['text']
    await callback.message.edit_text("⏳ Начинаю рассылку...")
    await state.clear()

    from database.users import get_all_users
    users = await get_all_users()
    sent = 0
    failed = 0
    for user in users:
        try:
            await callback.bot.send_message(user['telegram_id'], text)
            sent += 1
            await asyncio.sleep(0.05)  # чтобы не спамить
        except Exception as e:
            failed += 1
            logger.warning(f"Не удалось отправить пользователю {user['telegram_id']}: {e}")
    await callback.message.edit_text(f"✅ Рассылка завершена. Отправлено: {sent}, ошибок: {failed}")
    # Возврат в админку
    await admin_back(callback)
    await callback.answer()


@router.callback_query(F.data == CALLBACK_PROMO)
async def admin_promo_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return

    from database.promocodes import get_all_promocodes
    promos = await get_all_promocodes(include_inactive=True)

    text = "🎫 **Управление промокодами**\n\n"
    if not promos:
        text += "Пока нет ни одного промокода."
    else:
        for p in promos:
            active = "✅" if p['is_active'] else "❌"
            valid = f"до {p['valid_until']}" if p['valid_until'] else "бессрочно"
            uses = f"{p['used_count']}/{p['max_uses'] if p['max_uses'] else '∞'}"
            text += f"• `{p['code']}` {p['discount_type']} {p['discount_value']} {active}\n"
            text += f"  {valid}, использований: {uses}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data=CALLBACK_PROMO_ADD)],
        [InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_back")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# Добавление промокода
@router.callback_query(F.data == CALLBACK_PROMO_ADD)
async def add_promo_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await state.set_state(AddPromo.waiting_for_code)
    await callback.message.edit_text(
        "➕ **Создание промокода**\n\n"
        "Введите код промокода (например, SALE20):",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AddPromo.waiting_for_code)
async def add_promo_code(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    if not code:
        await message.answer("❌ Код не может быть пустым")
        return
    await state.update_data(code=code)
    await state.set_state(AddPromo.waiting_for_type)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Процент", callback_data="type_percent"),
         InlineKeyboardButton(text="Фиксированная сумма", callback_data="type_fixed")]
    ])
    await message.answer("Выберите тип скидки:", reply_markup=kb)


@router.callback_query(AddPromo.waiting_for_type, F.data.in_({"type_percent", "type_fixed"}))
async def add_promo_type(callback: types.CallbackQuery, state: FSMContext):
    dtype = "percent" if callback.data == "type_percent" else "fixed"
    await state.update_data(discount_type=dtype)
    await state.set_state(AddPromo.waiting_for_value)
    await callback.message.edit_text(
        "Введите значение скидки:\n"
        "- для процента: число от 1 до 100\n"
        "- для фиксированной суммы: целое число (в рублях)"
    )
    await callback.answer()


@router.message(AddPromo.waiting_for_value)
async def add_promo_value(message: types.Message, state: FSMContext):
    try:
        value = int(message.text)
        data = await state.get_data()
        if data['discount_type'] == 'percent' and (value < 1 or value > 100):
            await message.answer("❌ Процент должен быть от 1 до 100")
            return
        if value <= 0:
            await message.answer("❌ Значение должно быть положительным")
            return
    except ValueError:
        await message.answer("❌ Введите целое число")
        return
    await state.update_data(discount_value=value)
    await state.set_state(AddPromo.waiting_for_valid_until)
    await message.answer(
        "Введите дату окончания действия (в формате ГГГГ-ММ-ДД) или отправьте '0', если бессрочно:"
    )


@router.message(AddPromo.waiting_for_valid_until)
async def add_promo_valid(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == '0':
        valid_until = None
    else:
        try:
            from datetime import datetime
            valid_until = datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД или 0")
            return
    await state.update_data(valid_until=valid_until)
    await state.set_state(AddPromo.waiting_for_max_uses)
    await message.answer(
        "Введите максимальное количество использований (целое число) или '0' для безлимита:"
    )


@router.message(AddPromo.waiting_for_max_uses)
async def add_promo_max(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == '0':
        max_uses = None
    else:
        try:
            max_uses = int(text)
            if max_uses <= 0:
                await message.answer("❌ Число должно быть положительным")
                return
        except ValueError:
            await message.answer("❌ Введите целое число")
            return
    data = await state.get_data()
    from database.promocodes import create_promocode
    try:
        promo_id = await create_promocode(
            code=data['code'],
            discount_type=data['discount_type'],
            discount_value=data['discount_value'],
            valid_until=str(data['valid_until']) if data['valid_until'] else None,
            max_uses=max_uses
        )
        await message.answer(f"✅ Промокод {data['code']} создан (ID={promo_id})")
    except Exception as e:
        logger.error(f"Ошибка создания промокода: {e}")
        await message.answer("❌ Ошибка при создании промокода (возможно, такой код уже существует)")
    await state.clear()
    # Возврат в меню промокодов
    # Создадим новый callback для перехода
    # Можно просто вызвать admin_promo_menu через создание нового callback-запроса, но проще показать кнопку
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К списку промокодов", callback_data=CALLBACK_PROMO)]
    ])
    await message.answer("Что дальше?", reply_markup=kb)


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    """Возврат в главное меню админки"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
        [types.InlineKeyboardButton(text="📝 Управление товарами", callback_data="admin_manage_products")],
        [types.InlineKeyboardButton(text="📂 Управление категориями", callback_data="admin_categories")],
        [types.InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [types.InlineKeyboardButton(text="🏠 В главное меню", callback_data="go_home")]
    ])

    await callback.message.edit_text(
        f"🛠️ <b>Админ-панель магазина</b>\n\n"
        f"Выберите действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()