from aiogram import Router, types, F
from keyboards.main_menu import main_menu_keyboard

router = Router()

@router.callback_query(F.data == "contacts")
async def show_contacts(callback: types.CallbackQuery):
    await callback.message.answer(
        "📞 Наши контакты:\n\n"
        "Телефон: +7 999 083-51-98\n"
        "Адрес: г. Хабаровск, ул. Панькова, 15\n"
        "Время работы: 10:00 - 20:00\n\n"
        "TG: @nicholasfil!",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()