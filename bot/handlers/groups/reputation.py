from aiogram import Router, types, F
from bot.utils.db_manager import (
    update_reputation, get_top_reputation, get_mention_by_id,
    update_user_cache
)
from bot.utils.filters import ModuleEnabledFilter
import logging

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("reputation"))

# Ключевые слова для повышения репутации
PLUS_KEYWORDS = {"+", "спс", "спасибо", "лайк", "благодарю", "thx", "thanks", "респект"}
# Ключевые слова для понижения репутации
MINUS_KEYWORDS = {"-", "дизлайк", "отстой", "фу", "dislike"}

@router.message(F.reply_to_message)
async def handle_reputation_change(message: types.Message):
    """Изменяет репутацию при ответе на сообщение."""
    text = message.text.lower().strip() if message.text else ""
    
    # Проверяем, является ли текст команды изменением репутации
    is_plus = text in PLUS_KEYWORDS or (len(text) > 0 and text[0] == '+' and (len(text) == 1 or not text[1].isdigit()))
    is_minus = text in MINUS_KEYWORDS or (len(text) > 0 and text[0] == '-' and (len(text) == 1 or not text[1].isdigit()))
    
    if not is_plus and not is_minus:
        return

    target_user = message.reply_to_message.from_user
    source_user = message.from_user

    # Нельзя менять репутацию самому себе
    if target_user.id == source_user.id:
        await message.reply("❌ Вы не можете изменять репутацию самому себе.")
        return

    # Нельзя менять репутацию ботам
    if target_user.is_bot:
        return

    delta = 1 if is_plus else -1
    
    # Обновляем кэш пользователей
    await update_user_cache(target_user)
    await update_user_cache(source_user)

    stats = await update_reputation(message.chat.id, target_user.id, delta)
    
    target_mention = await get_mention_by_id(target_user.id)
    action_text = "повысил" if delta > 0 else "понизил"
    sign = "📈" if delta > 0 else "📉"
    
    await message.answer(
        f"{sign} {message.from_user.full_name} <b>{action_text}</b> её {target_mention}!\n"
        f"✨ <b>{stats['points']}</b>",
        parse_mode="HTML"
    )

@router.message(F.text.lower().in_({"топ реп", "топ репутации", "реп топ"}))
async def handle_reputation_top(message: types.Message):
    """Выводит топ репутации чата."""
    top_data = await get_top_reputation(message.chat.id)
    
    if not top_data:
        await message.reply("В этом чате пока никто не заработал репутацию.")
        return

    text = "<b>🏆 Топ чата</b>\n\n"
    for i, item in enumerate(top_data, 1):
        points = item["points"]
        user_data = item.get("users", {})
        name = user_data.get("nickname") or user_data.get("full_name") or f"ID: {item['user_id']}"
        
        medal = ""
        if i == 1: medal = "🥇 "
        elif i == 2: medal = "🥈 "
        elif i == 3: medal = "🥉 "
        else: medal = f"{i}. "
        
        text += f"{medal}<b>{name}</b> — <code>{points}</code>\n"

    await message.answer(text, parse_mode="HTML")
