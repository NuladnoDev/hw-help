from aiogram import types
from datetime import datetime, timedelta
from bot.utils.db_manager import add_mute, remove_mute, get_user_mention_with_nickname, get_mention_by_id
import re

async def mute_user(message: types.Message, target_user_id: int, command_args: str):
    """
    Применяет мут к пользователю в Telegram и записывает в БД.
    """
    # Парсинг времени (например, 10м, 1ч, 1д)
    duration_match = re.search(r'(\d+)([мчд])', command_args.lower())
    reason_match = re.search(r'(?:^|\s)(?:причина\s+)?(.+)', command_args.replace(duration_match.group(0) if duration_match else "", "").strip())
    
    until_date = None
    time_str = "навсегда"
    
    if duration_match:
        amount = int(duration_match.group(1))
        unit = duration_match.group(2)
        
        if unit == 'м':
            until_date = datetime.now() + timedelta(minutes=amount)
            time_str = f"{amount} мин."
        elif unit == 'ч':
            until_date = datetime.now() + timedelta(hours=amount)
            time_str = f"{amount} час."
        elif unit == 'д':
            until_date = datetime.now() + timedelta(days=amount)
            time_str = f"{amount} дн."

    reason = reason_match.group(1) if reason_match else "не указана"

    try:
        # Накладываем ограничения в Telegram
        # can_send_messages=False запрещает писать вообще что-либо
        permissions = types.ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        await message.chat.restrict(
            user_id=target_user_id,
            permissions=permissions,
            until_date=until_date
        )
        
        # Сохраняем в БД для защиты от перезахода
        add_mute(message.chat.id, target_user_id, until_date)
        
        # Уведомление с учетом никнеймов
        target_mention = get_mention_by_id(target_user_id)
        expiry_str = until_date.strftime("%d.%m.%Y %H:%M") if until_date else "бессрочно"
        
        await message.answer(
            f"🤐 <b>Пользователь замучен:</b> {target_mention}\n\n"
            f"⏰ <b>Срок:</b> {time_str}\n"
            f"📅 <b>Истекает:</b> {expiry_str}\n"
            f"📝 <b>Причина:</b> {reason}",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка при выполнении мута: {e}")

async def unmute_user(message: types.Message, target_user_id: int):
    """
    Снимает мут с пользователя.
    """
    try:
        # Возвращаем стандартные права
        permissions = types.ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_invite_users=True
        )
        
        await message.chat.restrict(
            user_id=target_user_id,
            permissions=permissions
        )
        
        remove_mute(message.chat.id, target_user_id)
        
        target_mention = get_mention_by_id(target_user_id)
        await message.answer(
            f"🔊 <b>Пользователь размучен:</b> {target_mention}",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка при размуте: {e}")
