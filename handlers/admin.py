from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

# Импортируем существующий список товаров из products.py
from handlers.products import products

router = Router()
logger = logging.getLogger(__name__)

# === НАСТРОЙКА ПРАВ ДОСТУПА ===
ADMIN_IDS = {524082641}  # Пока только ваш ID, позже добавим других


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


# === FSM (Finite State Machine) ДЛЯ ДОБАВЛЕНИЯ ТОВАРА ===
class AddProduct(StatesGroup):
    """Состояния для добавления нового товара"""
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()


# === КОМАНДА /admin ДЛЯ ВЫЗОВА АДМИНКИ ===
@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Основная команда админ-панели"""
    if not is_admin(message.from_user.id):
        logger.warning(f"⚠️ Неавторизованный доступ к админке от {message.from_user.id}")
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return

    # Клавиатура админ-меню
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
        [types.InlineKeyboardButton(text="📝 Управление товарами", callback_data="admin_manage_products")],
        [types.InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [types.InlineKeyboardButton(text="🏠 В главное меню", callback_data="go_home")]
    ])

    await message.answer(
        "🛠️ <b>Админ-панель магазина</b>\n\n"
        "Выберите действие:",
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


# === ОБРАБОТКА ЦЕНЫ И ФИНАЛИЗАЦИЯ ===
@router.message(AddProduct.waiting_for_price)
async def process_product_price(message: types.Message, state: FSMContext):
    """Получаем цену и сохраняем товар"""
    try:
        # Пробуем преобразовать в число
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

    # Получаем все сохранённые данные
    data = await state.get_data()
    await state.clear()

    # Создаём новый товар
    new_product = {
        "id": len(products) + 1,  # Простой способ генерации ID
        "name": data['name'],
        "description": data['description'],
        "price": price
    }

    # Добавляем в список товаров
    products.append(new_product)

    logger.info(f"🆕 Админ добавил товар: {new_product['name']} за {price}₽")

    # Показываем результат
    await message.answer(
        f"✅ <b>Товар успешно добавлен!</b>\n\n"
        f"🆔 ID: {new_product['id']}\n"
        f"📦 Название: {new_product['name']}\n"
        f"📝 Описание: {new_product['description']}\n"
        f"💰 Цена: {new_product['price']}₽\n\n"
        f"Теперь он доступен в каталоге для всех пользователей.",
        parse_mode="HTML"
    )

    # Предлагаем дальше
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ Добавить ещё товар", callback_data="admin_add_product")],
        [types.InlineKeyboardButton(text="📦 Перейти в каталог", callback_data="show_catalog")],
        [types.InlineKeyboardButton(text="🏠 В главное меню", callback_data="go_home")]
    ])

    await message.answer("Что дальше?", reply_markup=keyboard)


# === ОБРАБОТЧИК ОТМЕНЫ (на всякий случай) ===
@router.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Отмена текущего действия в админке"""
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    await callback.answer()


# === ЗАГЛУШКИ ДЛЯ ДРУГИХ ФУНКЦИЙ (доделаем завтра) ===
@router.callback_query(F.data == "admin_manage_products")
async def manage_products(callback: types.CallbackQuery):
    """Управление товарами (заглушка)"""
    await callback.message.edit_text(
        "📝 <b>Управление товарами</b>\n\n"
        "Здесь можно редактировать и удалять товары.\n\n"
        "<i>Эта функция будет доступна завтра!</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    """Статистика (заглушка)"""
    from handlers.products import user_carts

    total_products = len(products)
    total_carts = len(user_carts)

    await callback.message.edit_text(
        f"📊 <b>Статистика магазина</b>\n\n"
        f"📦 Товаров в каталоге: {total_products}\n"
        f"🛒 Активных корзин: {total_carts}\n\n"
        f"<i>Детальная статистика будет завтра!</i>",
        parse_mode="HTML"
    )
    await callback.answer()