from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

class ModAction(CallbackData, prefix="mod"):
    action: str
    user_id: int

def get_auto_ban_kb(user_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для сообщения об автоматическом перебане.
    Кнопки в одну строку: Убрать | Разблокировать
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🗑️ Убрать", 
                callback_data=ModAction(action="delete_msg", user_id=0).pack()
            ),
            InlineKeyboardButton(
                text="✅ Разблокировать", 
                callback_data=ModAction(action="unban", user_id=user_id).pack()
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
