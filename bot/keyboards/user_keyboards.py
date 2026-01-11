from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_start_kb(bot_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Кнопка "Добавить в чат"
    # Используем deep linking для добавления в группу
    builder.row(InlineKeyboardButton(
        text="➕ Добавить в чат",
        url=f"https://t.me/{bot_username}?startgroup=true"
    ))
    
    return builder.as_markup()
