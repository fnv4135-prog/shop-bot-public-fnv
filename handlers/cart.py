import logging
import asyncio
import config
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_cart_items, clear_cart, save_order
from utils import gsheets
from config import ADMIN_ID

logger = logging.getLogger(__name__)
router = Router()


class PromoState(StatesGroup):
    waiting_for_code = State()


async def show_cart_handler(message: types.Message, user_id: int = None):
    """Показать корзину пользователя"""
    if user_id is None:
        user_id = message.from_user.id

    cart_items = await get_cart_items(user_id)

    if not cart_items:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")]
        ])

        if hasattr(message, 'edit_text'):
            await message.edit_text(
                "🛒 <b>Ваша корзина пуста</b>\n\n"
                "Добавьте товары из каталога!",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "🛒 <b>Ваша корзина пуста</b>\n\n"
                "Добавьте товары из каталога!",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        return

    total = sum(item['price'] * item['quantity'] for item in cart_items)
    total_items = sum(item['quantity'] for item in cart_items)

    cart_text = "🛒 <b>Ваша корзина:</b>\n\n"
    for i, item in enumerate(cart_items, 1):
        cart_text += f"{i}. {item['name']} - {item['price']}₽ × {item['quantity']}\n"

    cart_text += f"\n<b>Товаров: {total_items}</b>\n<b>Итого: {total}₽</b>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="create_order")],
        [InlineKeyboardButton(text="🎫 Ввести промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="ask_clear_cart")],
        [
            InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")
        ]
    ])

    if hasattr(message, 'edit_text'):
        await message.edit_text(cart_text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(cart_text, reply_markup=keyboard, parse_mode="HTML")


@router.message(Command("cart"))
async def cmd_cart(message: types.Message):
    await show_cart_handler(message)


@router.callback_query(lambda c: c.data == "view_cart")
async def callback_show_cart(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_cart_handler(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(lambda c: c.data == "ask_clear_cart")
async def ask_clear_cart(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Да, очистить корзину", callback_data="confirm_clear_cart")],
        [InlineKeyboardButton(text="↩️ Нет, вернуться", callback_data="view_cart")]
    ])

    await callback.message.edit_text(
        "⚠️ <b>Вы уверены, что хотите очистить корзину?</b>\n\n"
        "Все товары будут удалены без возможности восстановления.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "confirm_clear_cart")
async def confirm_clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    success = await clear_cart(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog")],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")]
    ])

    if success:
        await callback.message.edit_text(
            "🗑 <b>Корзина очищена!</b>\n\n"
            "Все товары удалены.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка при очистке корзины</b>\n\n"
            "Попробуйте позже.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    await callback.answer("Корзина очищена!" if success else "Ошибка", show_alert=False)


@router.callback_query(lambda c: c.data == "create_order")
async def create_order(callback: types.CallbackQuery):
    """Оформление заказа (предварительный экран)"""
    user_id = callback.from_user.id
    cart_items = await get_cart_items(user_id)

    if not cart_items:
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    total = sum(item['price'] * item['quantity'] for item in cart_items)
    total_items = sum(item['quantity'] for item in cart_items)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton(text="🔙 Назад в корзину", callback_data="view_cart")]
    ])

    await callback.message.edit_text(
        f"✅ <b>Оформление заказа</b>\n\n"
        f"Товаров: {total_items}\n"
        f"Сумма: {total}₽\n\n"
        f"Для оформления нажмите 'Подтвердить заказ'.\n"
        f"Администратор свяжется с вами в ближайшее время.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "confirm_order")
async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
    try:
        # Проверяем, есть ли промокод в состоянии
        data = await state.get_data()
        promo_id = data.get('promocode_id')
        discounted_total = data.get('discounted_total')
        discount = data.get('discount', 0)
        # Если есть промокод, используем его для подсчёта, иначе считаем как обычно
        # Но нам нужно передать promo_id в save_order
        # Остальной код остаётся тем же, только total заменяем на discounted_total, если он есть
        user_id = callback.from_user.id
        username = callback.from_user.username or ""
        first_name = callback.from_user.first_name or ""
        last_name = callback.from_user.last_name or ""

        cart_items = await get_cart_items(user_id)
        if not cart_items:
            await callback.answer("❌ Корзина пуста!", show_alert=True)
            return

        if discounted_total is None:
            total = sum(item['price'] * item['quantity'] for item in cart_items)
        else:
            total = discounted_total
        total_items = sum(item['quantity'] for item in cart_items)

        order_id = await save_order(
            telegram_id=user_id,
            cart_items=cart_items,
            total=total,
            username=username,
            first_name=first_name,
            last_name=last_name,
            promocode_id=promo_id
        )

        success = await clear_cart(user_id)

        # Уведомление админу
        if success and not config.is_demo_mode():
            try:
                items_list = "\n".join(
                    [f"  • {item['name']} x{item['quantity']} - {item['price']}₽" for item in cart_items])
                admin_message = (
                    f"🆕 <b>Новый заказ #{order_id}</b>\n\n"
                    f"👤 Пользователь: @{callback.from_user.username} (ID: {user_id})\n"
                    f"💰 Сумма: {total}₽\n"
                    f"📦 Товары:\n{items_list}\n\n"
                    f"Статус: ожидает обработки"
                )
                await callback.bot.send_message(ADMIN_ID, admin_message, parse_mode="HTML")
                logger.info(f"📨 Уведомление о заказе #{order_id} отправлено админу")
            except Exception as e:
                logger.error(f"❌ Не удалось отправить уведомление админу: {e}")

        asyncio.create_task(gsheets.log_order_created(
            user_id=user_id,
            username=username,
            order_id=order_id,
            total=total,
            items_count=total_items
        ))

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")]
        ])

        if success and order_id:
            await callback.message.edit_text(
                f"🎉 <b>Заказ оформлен!</b>\n\n"
                f"🆔 Номер заказа: #{order_id}\n"
                f"💰 Сумма: {total}₽\n"
                f"📦 Товаров: {total_items}\n\n"
                f"Администратор свяжется с вами для уточнения деталей.\n"
                f"Спасибо за покупку! 🛍",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer("✅ Заказ оформлен!", show_alert=True)
        else:
            await callback.message.edit_text(
                "❌ <b>Ошибка при оформлении заказа</b>\n\nПопробуйте позже.",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer("❌ Ошибка", show_alert=True)

    except Exception as e:
        logger.exception(f"🔥 Критическая ошибка в confirm_order для user {callback.from_user.id}: {e}")
        await callback.answer("Произошла внутренняя ошибка. Мы уже знаем о ней.", show_alert=True)
        try:
            await callback.message.answer("⚠️ Произошла ошибка при оформлении заказа. Попробуйте ещё раз позже.")
        except:
            pass


@router.callback_query(lambda c: c.data == "enter_promo")
async def enter_promo(callback: types.CallbackQuery, state: FSMContext):
    """Запрос промокода"""
    cart_items = await get_cart_items(callback.from_user.id)
    if not cart_items:
        await callback.answer("Корзина пуста!", show_alert=True)
        return
    await state.set_state(PromoState.waiting_for_code)

    # Добавляем кнопку отмены
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="view_cart")]
    ])
    await callback.message.edit_text(
        "🎫 Введите промокод:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(PromoState.waiting_for_code)
async def process_promo(message: types.Message, state: FSMContext):
    """Обработка введённого промокода"""
    code = message.text.strip()
    from database.promocodes import get_promocode
    promo = await get_promocode(code)
    if not promo:
        await message.answer("❌ Промокод недействителен или истёк. Попробуйте ещё раз.")
        return

    # Сохраняем промокод в состоянии сессии (или в БД временно)
    await state.update_data(promocode_id=promo['id'], discount_type=promo['discount_type'],
                            discount_value=promo['discount_value'])
    # Показываем корзину с учётом скидки
    user_id = message.from_user.id
    cart_items = await get_cart_items(user_id)
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    total_items = sum(item['quantity'] for item in cart_items)

    # Применяем скидку
    if promo['discount_type'] == 'percent':
        discount = total * promo['discount_value'] // 100
    else:
        discount = min(promo['discount_value'], total)  # не больше суммы
    new_total = total - discount

    # Сохраняем сумму со скидкой в состоянии
    await state.update_data(discounted_total=new_total, discount=discount)

    # Показываем обновлённую корзину
    cart_text = f"🛒 <b>Ваша корзина (с промокодом {code}):</b>\n\n"
    for i, item in enumerate(cart_items, 1):
        cart_text += f"{i}. {item['name']} - {item['price']}₽ × {item['quantity']}\n"
    cart_text += f"\n<b>Товаров: {total_items}</b>\n"
    if discount > 0:
        cart_text += f"<b>Скидка: -{discount}₽</b>\n"
    cart_text += f"<b>Итого: {new_total}₽</b>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="create_order_with_promo")],
        [InlineKeyboardButton(text="🎫 Другой промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="ask_clear_cart")],
        [
            InlineKeyboardButton(text="🛍 В каталог", callback_data="show_catalog"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="go_home")
        ]
    ])

    await message.answer(cart_text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(None)  # можно оставить состояние для оформления, но лучше новый обработчик


@router.callback_query(lambda c: c.data == "create_order_with_promo")
async def create_order_with_promo(callback: types.CallbackQuery, state: FSMContext):
    """Оформление заказа с промокодом"""
    data = await state.get_data()
    promo_id = data.get('promocode_id')
    discounted_total = data.get('discounted_total')
    # Вызываем обычный confirm_order, но передаём туда promo_id и сумму
    # Можно немного переделать confirm_order, чтобы он принимал необязательные параметры
    # Я для простоты вызову confirm_order, но внутри него нужно будет учесть промокод.
    # Давай проще: создадим нового обработчика, который будет делать всё то же, что и confirm_order, но с учётом промокода.
    # Но чтобы не дублировать код, лучше модифицировать существующий confirm_order.
    # Поступим так: в confirm_order будем проверять, есть ли промокод в состоянии, и если есть, применяем его.
    await confirm_order(callback, state, promo_applied=True)