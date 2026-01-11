import random
from aiogram import Router, types, F
from aiogram.filters.callback_data import CallbackData
from bot.utils.db_manager import (
    get_mention_by_id, 
    update_relationship, 
    get_relationship,
    get_all_user_relationships,
    delete_relationship
)
from bot.handlers.groups.moderation import get_target_id
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

# Callback data для отношений
class RelCallback(CallbackData, prefix="rel"):
    action: str
    user1_id: int
    user2_id: int

# Список доступных социальных действий
SOCIAL_ACTIONS = {
    "обнять": {
        "text": "{user1} обнял(а) {user2} 🤗",
        "emoji": "🤗",
        "declension": "обнял(а)"
    },
    "поцеловать": {
        "text": "{user1} поцеловал(а) {user2} 💋",
        "emoji": "💋",
        "declension": "поцеловал(а)"
    },
    "трахнуть": {
        "text": "{user1} жестко оттрахал(а) {user2} 🔞",
        "emoji": "🔞",
        "declension": "оттрахал(а)"
    },
    "ударить": {
        "text": "{user1} дал(а) пощечину {user2} 🖐",
        "emoji": "🖐",
        "declension": "ударил(а)"
    },
    "укусить": {
        "text": "{user1} укусил(а) {user2} за бочок 🦷",
        "emoji": "🦷",
        "declension": "укусил(а)"
    },
    "погладить": {
        "text": "{user1} нежно погладил(а) {user2} по голове 😊",
        "emoji": "😊",
        "declension": "погладил(а)"
    },
    "лизнуть": {
        "text": "{user1} лизнул(а) {user2} 👅",
        "emoji": "👅",
        "declension": "лизнул(а)"
    }
}

def get_relationship_level(total):
    if total < 5: return "Знакомые 👥"
    if total < 15: return "Друзья 🤝"
    if total < 30: return "Хорошие друзья ✨"
    if total < 60: return "Близкие люди ❤️"
    if total < 100: return "Лучшие друзья 🔥"
    if total < 200: return "Родственные души 💎"
    return "Неразлучная связь ♾"

@router.message(lambda message: any(message.text.lower().startswith(action) for action in SOCIAL_ACTIONS))
async def handle_social_action(message: types.Message):
    text = message.text.lower()
    action_key = None
    
    for action in SOCIAL_ACTIONS:
        if text.startswith(action):
            action_key = action
            break
            
    if not action_key:
        return

    target_user_id, _ = await get_target_id(message, action_key)
    
    if not target_user_id:
        await message.reply(f"❌ Укажите, кого вы хотите {action_key} (тег или ответ на сообщение).")
        return
        
    if target_user_id == message.from_user.id:
        await message.reply(f"🤔 Вы пытаетесь {action_key} самого себя? Это как?")
        return

    user1_mention = get_mention_by_id(message.from_user.id)
    user2_mention = get_mention_by_id(target_user_id)
    
    # Обновляем БД
    rel_data = update_relationship(message.from_user.id, target_user_id, action_key)
    
    action_info = SOCIAL_ACTIONS[action_key]
    result_text = action_info["text"].format(user1=user1_mention, user2=user2_mention)
    
    # Добавляем инфо об уровне отношений
    level = get_relationship_level(rel_data["total_interactions"])
    
    await message.answer(
        f"{result_text}\n\n"
        f"📊 <b>Отношения:</b> {level} (взаимодействий: {rel_data['total_interactions']})",
        parse_mode="HTML"
    )

@router.message(F.text.lower() == "наши отношения")
async def show_pair_relationships(message: types.Message):
    if not message.reply_to_message:
        await message.reply("❌ Ответьте на сообщение пользователя, чтобы посмотреть ваши отношения с ним.")
        return
        
    target_id = message.reply_to_message.from_user.id
    if target_id == message.from_user.id:
        await message.reply("🤡 Отношения с самим собой всегда прекрасны!")
        return
        
    rel_data = get_relationship(message.from_user.id, target_id)
    target_mention = get_mention_by_id(target_id)
    
    if not rel_data:
        await message.reply(f"🤷‍♂️ У вас пока нет истории отношений с {target_mention}.", parse_mode="HTML")
        return
        
    level = get_relationship_level(rel_data.get("total_interactions", 0))
    
    actions_text = ""
    for action, count in rel_data.get("actions", {}).items():
        emoji = SOCIAL_ACTIONS.get(action, {}).get("emoji", "🔘")
        actions_text += f"\n{emoji} {action.capitalize()}: {count}"
        
    last_interaction = rel_data.get("last_interaction", "Неизвестно")
    if "T" in last_interaction:
        last_interaction = last_interaction[:16].replace('T', ' ')

    await message.reply(
        f"📜 <b>История отношений с {target_mention}</b>\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"📈 <b>Уровень:</b> {level}\n"
        f"🔄 <b>Всего взаимодействий:</b> {rel_data.get('total_interactions', 0)}\n"
        f"📅 <b>Последнее:</b> {last_interaction}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🎭 <b>Статистика действий:</b>{actions_text}",
        parse_mode="HTML"
    )

@router.message(F.text.lower().in_({"мои отношения", "мои отн", "отн стата"}))
async def show_my_relationships(message: types.Message):
    """
    Показывает список всех отношений пользователя.
    """
    relationships = get_all_user_relationships(message.from_user.id)
    
    if not relationships:
        await message.reply("👀 У вас пока нет истории отношений с кем-либо. Попробуйте обнять или поцеловать кого-нибудь!")
        return
        
    response = "📊 <b>Ваши отношения:</b>\n"
    response += "➖➖➖➖➖➖➖➖➖➖\n"
    
    # Показываем топ-10 отношений
    for i, rel in enumerate(relationships[:10], 1):
        partner_mention = get_mention_by_id(rel["partner_id"])
        level = get_relationship_level(rel["data"]["total_interactions"])
        count = rel["data"]["total_interactions"]
        response += f"{i}. {partner_mention} — {level} ({count})\n"
        
    if len(relationships) > 10:
        response += f"\n<i>...и еще {len(relationships) - 10} отношений.</i>"
        
    response += "\n➖➖➖➖➖➖➖➖➖➖\n"
    response += "💡 <i>Ответьте на сообщение пользователя командой 'наши отношения', чтобы увидеть детали.</i>"
    
    await message.answer(response, parse_mode="HTML")

@router.message(F.text.lower().startswith("+отн"))
async def propose_relationship(message: types.Message):
    """
    Предложение начать отношения.
    """
    target_user_id, _ = await get_target_id(message, "+отн")
    
    if not target_user_id:
        await message.reply("❌ Укажите, с кем вы хотите начать отношения (тег или ответ на сообщение).")
        return
        
    if target_user_id == message.from_user.id:
        await message.reply("🤡 Отношения с самим собой — это база, но приглашение не требуется.")
        return

    user1_mention = get_mention_by_id(message.from_user.id)
    user2_mention = get_mention_by_id(target_user_id)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Принять", callback_data=RelCallback(action="accept", user1_id=message.from_user.id, user2_id=target_user_id))
    kb.button(text="❌ Отклонить", callback_data=RelCallback(action="decline", user1_id=message.from_user.id, user2_id=target_user_id))
    kb.adjust(2)
    
    await message.answer(
        f"💖 {user2_mention}, пользователь {user1_mention} предлагает вам начать отношения!\n"
        f"Вы согласны?",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(RelCallback.filter())
async def handle_rel_callback(callback: types.CallbackQuery, callback_data: RelCallback):
    if callback.from_user.id != callback_data.user2_id:
        await callback.answer("❌ Это приглашение не для вас!", show_alert=True)
        return
        
    user1_mention = get_mention_by_id(callback_data.user1_id)
    user2_mention = get_mention_by_id(callback_data.user2_id)
    
    if callback_data.action == "accept":
        # Инициализируем отношения, если их нет (первое действие "начало")
        update_relationship(callback_data.user1_id, callback_data.user2_id, "начало")
        await callback.message.edit_text(
            f"🎉 Поздравляем! {user1_mention} и {user2_mention} теперь в отношениях! ❤️",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"💔 {user2_mention} отклонил(а) предложение {user1_mention}.",
            parse_mode="HTML"
        )

@router.message(F.text.lower().in_({"-отн", "-отношения"}))
async def remove_relationship(message: types.Message):
    """
    Удаление отношений.
    """
    if not message.reply_to_message:
        await message.reply("❌ Ответьте на сообщение пользователя, с которым хотите разорвать отношения.")
        return
        
    target_id = message.reply_to_message.from_user.id
    if target_id == message.from_user.id:
        await message.reply("🤡 Нельзя разорвать отношения с самим собой.")
        return
        
    rel_data = get_relationship(message.from_user.id, target_id)
    if not rel_data:
        await message.reply("🤷‍♂️ У вас и так нет истории отношений с этим пользователем.")
        return
        
    delete_relationship(message.from_user.id, target_id)
    target_mention = get_mention_by_id(target_id)
    
    await message.reply(
        f"💔 Отношения с {target_mention} были разорваны. Вся история взаимодействий удалена.",
        parse_mode="HTML"
    )
