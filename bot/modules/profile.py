from aiogram import types
from bot.utils.db_manager import (
    get_nickname, get_user_stats, get_description, 
    get_rank, get_mention_by_id, get_user_rank_context,
    get_marriage
)
from bot.keyboards.profile_keyboards import get_profile_kb
from datetime import datetime

def get_relative_time(dt: datetime) -> str:
    """
    Возвращает строку вида '2 дня назад' или '5 минут назад'.
    """
    diff = datetime.now() - dt
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return "только что"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} мин. назад"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} ч. назад"
    else:
        days = seconds // 86400
        return f"{days} дн. назад"

async def get_user_profile(message: types.Message, target_user_id: int):
    """
    Формирует и отправляет профиль пользователя в новом формате.
    """
    # Получаем данные из БД
    custom_nick = await get_nickname(target_user_id)
    stats = await get_user_stats(target_user_id)
    
    # Пытаемся получить инфо о пользователе через Telegram
    try:
        member = await message.chat.get_member(target_user_id)
        user = member.user
        
        # Определяем имя для отображения: ник -> @тег -> имя
        display_name = custom_nick
        if not display_name:
            display_name = f"@{user.username}" if user.username else user.full_name
            
        user_mention = user.mention_html(display_name)
        
        # Попутно обновляем кэш свежими данными
        from bot.utils.db_manager import update_user_cache
        await update_user_cache(user.id, user.username, user.full_name)
    except Exception:
        # Если не удалось получить инфо из Telegram, используем наш кэш/никнейм
        user_mention = await get_mention_by_id(target_user_id)

    rank_level, rank_name, is_super = await get_user_rank_context(target_user_id, message.chat)
    description = await get_description(target_user_id)
    marriage = await get_marriage(target_user_id)
    
    # Форматирование дат
    first_app_str = datetime.fromisoformat(stats["first_appearance"]).strftime("%d.%m.%Y")
    
    profile_text = f"👤 Это пользователь {user_mention}\n"
    
    if description:
        profile_text += f"{description}\n"
        
    profile_text += (
        f"\n"
        f"🎖 <b>Ранг:</b> {rank_name}\n"
    )

    if marriage:
        partner_id = [p for p in marriage["partners"] if p != target_user_id][0]
        partner_mention = await get_mention_by_id(partner_id)
        profile_text += f"💍 <b>В браке с:</b> {partner_mention}\n"

    profile_text += (
        f"📅 <b>Впервые замечен:</b> {first_app_str}\n"
        f"📊 <b>Статус:</b> {'Бот' if 'user' in locals() and getattr(user, 'is_bot', False) else 'Пользователь'}"
    )
    
    await message.answer(
        profile_text, 
        parse_mode="HTML",
        reply_markup=get_profile_kb(target_user_id)
    )
