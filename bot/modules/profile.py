from aiogram import types
from bot.utils.db_manager import (
    get_mention_by_id, get_user_rank_context,
    get_user_profile_data, get_group_rank_name
)
from bot.keyboards.profile_keyboards import get_profile_kb
from datetime import datetime, timezone

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
    Оптимизировано для быстрой работы.
    """
    # 1. Сначала получаем все данные из БД одним пакетом
    db_data = await get_user_profile_data(target_user_id, message.chat.id)
    
    # 2. Пытаемся получить информацию из Telegram (только если нужно)
    try:
        # Используем кэш из db_data, если там есть ник
        display_name = db_data.get("nickname")
        
        # Если в чате, пробуем получить актуальное имя
        member = await message.chat.get_member(target_user_id)
        user = member.user
        
        if not display_name:
            display_name = f"@{user.username}" if user.username else user.full_name
            
        user_mention = user.mention_html(display_name)
        
        # Проверяем на создателя чата для ранга
        if member.status == "creator" and db_data["rank_level"] < 5:
            db_data["rank_level"] = 5
            
    except Exception:
        # Если не удалось получить инфо из Telegram, используем get_mention_by_id (он тоже лезет в БД, но это крайний случай)
        user_mention = await get_mention_by_id(target_user_id)

    # 3. Получаем название ранга с учетом падежа (может быть в кэше БД)
    rank_name = await get_group_rank_name(message.chat.id, db_data["rank_level"], "nom")
    
    # Форматирование дат
    first_app_dt = datetime.fromisoformat(db_data["first_appearance"])
    first_app_str = first_app_dt.strftime("%d.%m.%Y")
    
    profile_text = f"👤 Это пользователь {user_mention}\n"
    
    if db_data.get("description"):
        profile_text += f"{db_data['description']}\n"
        
    profile_text += (
        f"\n"
        f"🎖 <b>Ранг:</b> {rank_name}\n"
    )

    if db_data.get("city"):
        profile_text += f"🏙 <b>Город:</b> {db_data['city']}\n"

    marriage = db_data.get("marriage")
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
        reply_markup=get_profile_kb(target_user_id, has_quote=bool(db_data.get("quote")))
    )
