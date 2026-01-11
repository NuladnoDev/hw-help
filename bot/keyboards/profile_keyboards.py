from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

class ProfileAction(CallbackData, prefix="profile"):
    action: str
    user_id: int

def get_profile_kb(user_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для профиля пользователя.
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="📝 Описание", 
                callback_data=ProfileAction(action="description", user_id=user_id).pack()
            ),
            InlineKeyboardButton(
                text="🏆 Награды", 
                callback_data=ProfileAction(action="awards", user_id=user_id).pack()
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
