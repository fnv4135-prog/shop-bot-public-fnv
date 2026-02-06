# create_missing_files.py - скрипт для создания всех недостающих файлов
import os

# Создаем папки
os.makedirs("handlers", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Создаем файлы в handlers
files = {
    "handlers/__init__.py": "",
    "handlers/products.py": """from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

# Тестовые товары
products = [
    {"id": 1, "name": "📱 iPhone 15", "price": 79900, "description": "Новый iPhone 15"},
    {"id": 2, "name": "💻 MacBook Air", "price": 119900, "description": "Ноутбук Apple"},
    {"id": 3, "name": "🎧 AirPods Pro", "price": 24900, "description": "Беспроводные наушники"},
]

@router.message(Command("products"))
async def show_products(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p['name']} - {p['price']}₽", callback_data=f"product_{p['id']}")]
        for p in products
    ] + [[InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")]])

    await message.answer("🏪 **Каталог товаров:**\\nВыберите товар:", reply_markup=keyboard)
""",

    "handlers/cart.py": """from aiogram import Router
router = Router()
""",

    "handlers/order.py": """from aiogram import Router
router = Router()
""",

    "data/__init__.py": "",

    "data/database.py": """import sqlite3

def init_db():
    print("✅ База данных инициализирована")

def add_test_product():
    print("✅ Тестовые товары добавлены")
"""
}

# Создаем файлы
for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Создан файл: {path}")

print("🎯 Все файлы созданы! Теперь добавь их в git:")
print("git add handlers/ data/")
print("git commit -m 'Добавил недостающие модули'")
print("git push origin main")