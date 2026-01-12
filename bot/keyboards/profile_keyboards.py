from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

class ProfileAction(CallbackData, prefix="profile"):
    action: str
    user_id: int

def get_profile_kb(user_id: int, has_quote: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для профиля пользователя.
    """
    row1 = [
        InlineKeyboardButton(
            text="📝 Описание",
            callback_data=ProfileAction(action="description", user_id=user_id).pack()
        ),
        InlineKeyboardButton(
            text="⭐ Уровень",
            callback_data=ProfileAction(action="level", user_id=user_id).pack()
        ),
        InlineKeyboardButton(
            text="🏆 Награды",
            callback_data=ProfileAction(action="awards", user_id=user_id).pack()
        )
    ]
    
    buttons = [row1]
    
    if has_quote:
        buttons.append([
            InlineKeyboardButton(
                text="💬 Цитата", 
                callback_data=ProfileAction(action="quote", user_id=user_id).pack()
            )
        ])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_level_kb(user_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для экрана уровней.
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="⬅️ К профилю",
                callback_data=ProfileAction(action="back", user_id=user_id).pack()
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
