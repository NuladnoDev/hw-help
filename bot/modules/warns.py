from aiogram import types
from datetime import datetime, timedelta
from bot.utils.db_manager import add_warn, get_warns, remove_last_warn, remove_warn_by_index, clear_warns, get_user_mention_with_nickname, get_mention_by_id
import re

async def warn_user(message: types.Message, target_user_id: int, command_args: str):
    """
    Выдает предупреждение пользователю.
    """
    # Парсинг времени (например, 10м, 1ч, 1д)
    duration_match = re.search(r'(\d+)([мчд])', command_args.lower())
    
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

    # Извлекаем причину
    clean_args = command_args
    if duration_match:
        clean_args = command_args.replace(duration_match.group(0), "").strip()
    
    reason = clean_args if clean_args else "Не указана"
    
    # Добавляем в БД
    warn_count = await add_warn(message.chat.id, target_user_id, reason, until_date)
    
    # Получаем упоминания админа и цели с учетом никнеймов
    admin_mention = await get_user_mention_with_nickname(message.from_user)
    
    # Пытаемся получить упоминание цели. 
    if message.reply_to_message and message.reply_to_message.from_user.id == target_user_id:
        target_mention = await get_user_mention_with_nickname(message.reply_to_message.from_user)
    else:
        target_mention = await get_mention_by_id(target_user_id, "пользователю")

    # Формируем сообщение по новому формату
    response = f"⚠️ {admin_mention} выдал предупреждение {target_mention}\nПричина: {reason}"
    
    if until_date:
        expiry_str = until_date.strftime("%d.%m.%Y %H:%M")
        response += f"\n⏰ Срок: {time_str} (до {expiry_str})"
    
    await message.answer(response, parse_mode="HTML")

async def list_warns(message: types.Message, target_user_id: int):
    """
    Показывает список активных предупреждений пользователя.
    """
    warns = await get_warns(message.chat.id, target_user_id)
    target_mention = await get_mention_by_id(target_user_id)
    
    if not warns:
        await message.answer(f"✅ У {target_mention} нет активных предупреждений.", parse_mode="HTML")
        return
    
    response = f"📋 <b>Список предупреждений для {target_mention}:</b>\n\n"
    
    for i, warn in enumerate(warns, 1):
        date_str = datetime.fromisoformat(warn["date"]).strftime("%d.%m.%Y %H:%M")
        reason = warn["reason"]
        until = warn["until"]
        
        response += f"варн [{i}] | {reason} (от {date_str})"
        if until != "permanent" and until:
            until_date = datetime.fromisoformat(until).strftime("%d.%m.%Y %H:%M")
            response += f" — <i>до {until_date}</i>"
        response += "\n"
    
    response += f"\nЧтобы убрать конкретный варн, используйте команду:\n<code>-варн (тег) (номер варна)</code>"
        
    await message.answer(response, parse_mode="HTML")

async def remove_warn_index(message: types.Message, target_user_id: int, index: int):
    """
    Снимает предупреждение по его номеру.
    """
    target_mention = await get_mention_by_id(target_user_id)
    # Индекс от пользователя 1-based, переводим в 0-based
    if await remove_warn_by_index(message.chat.id, target_user_id, index - 1):
        await message.answer(f"✅ Предупреждение №{index} для {target_mention} снято.", parse_mode="HTML")
    else:
        await message.answer(f"❌ Не удалось найти предупреждение №{index} для {target_mention}.", parse_mode="HTML")

async def unwarn_user(message: types.Message, target_user_id: int):
    """
    Снимает последнее предупреждение.
    """
    target_mention = await get_mention_by_id(target_user_id)
    if await remove_last_warn(message.chat.id, target_user_id):
        await message.answer(f"✅ Последнее предупреждение для {target_mention} снято.", parse_mode="HTML")
    else:
        await message.answer(f"❌ У {target_mention} нет активных предупреждений.", parse_mode="HTML")

async def clear_user_warns(message: types.Message, target_user_id: int):
    """
    Снимает все предупреждения.
    """
    target_mention = await get_mention_by_id(target_user_id)
    if await clear_warns(message.chat.id, target_user_id):
        await message.answer(f"🧹 Все предупреждения для {target_mention} аннулированы.", parse_mode="HTML")
    else:
        await message.answer(f"❌ У {target_mention} нет активных предупреждений.", parse_mode="HTML")
