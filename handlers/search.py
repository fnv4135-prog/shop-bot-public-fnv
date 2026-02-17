"""
handlers/search.py - Поиск товаров по названию
"""
import logging
from aiogram import Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.products import search_products

router = Router()
logger = logging.getLogger(__name__)


class SearchStates(StatesGroup):
    waiting_for_query = State()


@router.callback_query(lambda c: c.data == "search")
@router.message(Command("search"))
async def start_search(event: types.Message | types.CallbackQuery, state: FSMContext):
    """Начинает процесс поиска: запрашивает строку для поиска"""
    await state.set_state(SearchStates.waiting_for_query)

    if isinstance(event, types.Message):
        await event.answer("🔍 Введите название товара для поиска:")
    else:  # callback
        await event.message.edit_text("🔍 Введите название товара для поиска:")
        await event.answer()


@router.message(SearchStates.waiting_for_query)
async def process_search(message: types.Message, state: FSMContext):
    """Выполняет поиск и показывает результаты"""
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("❌ Слишком короткий запрос. Введите минимум 2 символа.")
        return

    results = await search_products(query)
    await state.clear()

    if not results:
        await message.answer("😕 Ничего не найдено. Попробуйте другой запрос.")
        return

    # Формируем клавиатуру с результатами
    kb = []
    for prod in results:
        kb.append([InlineKeyboardButton(
            text=f"{prod['name']} - {prod['price']}₽",
            callback_data=f"product_{prod['id']}"
        )])
    # Добавляем кнопки навигации
    kb.append([
        InlineKeyboardButton(text="◀️ Назад в каталог", callback_data="show_catalog"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="go_home")
    ])

    await message.answer(
        f"🔍 Найдено товаров: {len(results)}\n\nВыберите товар:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )