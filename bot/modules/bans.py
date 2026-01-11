from aiogram import types
from aiogram.exceptions import TelegramBadRequest
import logging
from datetime import datetime, timedelta
from bot.utils.db_manager import get_mention_by_id
from bot.utils.db_manager import add_ban, remove_ban

async def ban_user(message: types.Message, user_id: int, duration: timedelta = None, reason: str = "Не указана"):
    """
    Функция для бана пользователя в чате.
    """
    until_date = None
    if duration:
        until_date = datetime.now() + duration

    try:
        await message.chat.ban(user_id=user_id, until_date=until_date)
        
        target_mention = await get_mention_by_id(user_id)
        ban_message = f"👤 {target_mention} был **забанен**."
        if duration:
            ban_message += f" До: {until_date.strftime('%d.%m.%Y %H:%M')}"
        ban_message += f"\n📝 Причина: {reason}"

        await message.answer(
            text=ban_message,
            parse_mode="HTML"
        )
        
    except TelegramBadRequest as e:
        logging.error(f"Ошибка при бане пользователя {user_id}: {e}")
        await message.answer("❌ Не удалось забанить пользователя. Проверьте мои права администратора.")
    except Exception as e:
        logging.error(f"Непредвиденная ошибка при бане: {e}")
        await message.answer("❌ Произошла ошибка при попытке бана.")

async def unban_user(message: types.Message, user_id: int):
    """
    Функция для разбана пользователя в чате.
    """
    try:
        await message.chat.unban(user_id=user_id, only_if_banned=True)
        await remove_ban(message.chat.id, user_id)
        
        target_mention = await get_mention_by_id(user_id)
        await message.answer(
            text=f"✅ {target_mention} был **разбанен**.",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        logging.error(f"Ошибка при разбане пользователя {user_id}: {e}")
        await message.answer("❌ Не удалось разбанить пользователя.")
