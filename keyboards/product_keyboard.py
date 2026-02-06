# keyboards/product_keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_product_keyboard(product_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для товара"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Добавить в корзину",
                    callback_data=f"add_to_cart_{product_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к каталогу",
                    callback_data="catalog"
                ),
                InlineKeyboardButton(
                    text="🏠 В главное меню",
                    callback_data="back_to_start"
                )
            ]
        ]
    )

def buy_keyboard(product_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для покупки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Купить сейчас",
                    callback_data=f"buy_now_{product_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"product_{product_id}"
                )
            ]
        ]
    )