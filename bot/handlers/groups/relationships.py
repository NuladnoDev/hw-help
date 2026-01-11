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
    "ударить тапком": {
        "text": "{user1} со всей силы ударил(а) тапком {user2} 🩴",
        "emoji": "🩴",
        "declension": "ударил(а) тапком"
    },
    "ударить кирпичом": {
        "text": "{user1} приложил(а) кирпичом {user2} 🧱",
        "emoji": "🧱",
        "declension": "ударил(а) кирпичом"
    },
    "ударить": {
        "text": "{user1} ударил(а) {user2} 🖐",
        "emoji": "🖐",
        "declension": "ударил(а)"
    },
    "укусить за ушко": {
        "text": "{user1} игриво укусил(а) за ушко {user2} 👂",
        "emoji": "👂",
        "declension": "укусил(а) за ушко"
    },
    "укусить": {
        "text": "{user1} укусил(а) {user2} 🦷",
        "emoji": "🦷",
        "declension": "укусил(а)"
    },
    "погладить по животику": {
        "text": "{user1} погладил(а) по животику {user2} ✨",
        "emoji": "✨",
        "declension": "погладил(а) по животику"
    },
    "погладить": {
        "text": "{user1} погладил(а) {user2} ✨",
        "emoji": "✨",
        "declension": "погладил(а)"
    },
    "лизнуть": {
        "text": "{user1} лизнул(а) {user2} 👅",
        "emoji": "👅",
        "declension": "лизнул(а)"
    },
    "убить": {
        "text": "{user1} жестко убил(а) {user2} 🔪",
        "emoji": "🔪",
        "declension": "убил(а)"
    },
    "послать": {
        "text": "{user1} послал(а) нахер {user2} 🖕",
        "emoji": "🖕",
        "declension": "послал(а)"
    },
    "напоить водой": {
        "text": "{user1} напоил(а) чистой водой {user2} 💧",
        "emoji": "💧",
        "declension": "напоил(а) водой"
    },
    "напоить чаем": {
        "text": "{user1} угостил(а) вкусным чаем {user2} ☕️",
        "emoji": "☕️",
        "declension": "напоил(а) чаем"
    },
    "напоить вином": {
        "text": "{user1} налил(а) бокал дорогого вина {user2} 🍷",
        "emoji": "🍷",
        "declension": "напоил(а) вином"
    },
    "напоить": {
        "text": "{user1} напоил(а) {user2} 🍻",
        "emoji": "🍻",
        "declension": "напоил(а)"
    },
    "связать": {
        "text": "{user1} крепко связал(а) {user2} ⛓",
        "emoji": "⛓",
        "declension": "связал(а)"
    },
    "унизить": {
        "text": "{user1} публично унизил(а) {user2} 🤡",
        "emoji": "🤡",
        "declension": "унизил(а)"
    },
    "покормить грудью": {
        "text": "{user1} нежно покормил(а) грудью {user2} 🍼",
        "emoji": "🍼",
        "declension": "покормил(а) грудью"
    },
    "покормить печеньками": {
        "text": "{user1} угостил(а) печеньками {user2} 🍪",
        "emoji": "🍪",
        "declension": "покормил(а) печеньками"
    },
    "покормить": {
        "text": "{user1} покормил(а) {user2} 🍲",
        "emoji": "🍲",
        "declension": "покормил(а)"
    },
    "ущипнуть": {
        "text": "{user1} больно ущипнул(а) {user2} 👌",
        "emoji": "👌",
        "declension": "ущипнул(а)"
    },
    "подмигнуть": {
        "text": "{user1} игриво подмигнул(а) {user2} 😉",
        "emoji": "😉",
        "declension": "подмигнул(а)"
    },
    "плюнуть": {
        "text": "{user1} плюнул(а) в лицо {user2} 💦",
        "emoji": "💦",
        "declension": "плюнул(а)"
    },
    "облизать": {
        "text": "{user1} полностью облизал(а) {user2} 🤤",
        "emoji": "🤤",
        "declension": "облизал(а)"
    },
    "шлепнуть": {
        "text": "{user1} звонко шлепнул(а) по заднице {user2} 🍑",
        "emoji": "🍑",
        "declension": "шлепнул(а)"
    },
    "отсосать": {
        "text": "{user1} сделал(а) качественный минет {user2} 🍌",
        "emoji": "🍌",
        "declension": "отсосал(а)"
    },
    "выпороть": {
        "text": "{user1} хорошенько выпорол(а) {user2} 🧨",
        "emoji": "🧨",
        "declension": "выпорол(а)"
    },
    "изнасиловать": {
        "text": "{user1} совершил(а) акт насилия над {user2} 🔞",
        "emoji": "🔞",
        "declension": "изнасиловал(а)"
    },
    "прижать": {
        "text": "{user1} сильно прижал(а) к стене {user2} 🧱",
        "emoji": "🧱",
        "declension": "прижал(а)"
    },
    "повалить": {
        "text": "{user1} повалил(а) на кровать {user2} 🛏",
        "emoji": "🛏",
        "declension": "повалил(а)"
    },
    "раздеть": {
        "text": "{user1} полностью раздевает {user2} 👕",
        "emoji": "👕",
        "declension": "раздел(а)"
    },
    "пощекотать": {
        "text": "{user1} до слез защекотал(а) {user2} 😂",
        "emoji": "😂",
        "declension": "пощекотал(а)"
    },
    "приласкать": {
        "text": "{user1} нежно приласкал(а) {user2} ✨",
        "emoji": "✨",
        "declension": "приласкал(а)"
    },
    "покусать": {
        "text": "{user1} искусал(а) всё тело {user2} 🧛",
        "emoji": "🧛",
        "declension": "покусал(а)"
    },
    "выпить": {
        "text": "{user1} выпил(а) на брудершафт с {user2} 🥂",
        "emoji": "🥂",
        "declension": "выпил(а)"
    },
    "сжечь": {
        "text": "{user1} заживо сжег(ла) {user2} 🔥",
        "emoji": "🔥",
        "declension": "сжег(ла)"
    },
    "закопать": {
        "text": "{user1} живьем закопал(а) в землю {user2} ⚰",
        "emoji": "⚰",
        "declension": "закопал(а)"
    },
    "убаюкать": {
        "text": "{user1} убаюкал(а) на руках {user2} 💤",
        "emoji": "💤",
        "declension": "убаюкал(а)"
    },
    "взять за руку": {
        "text": "{user1} крепко взял(а) за руку {user2} 🤝",
        "emoji": "🤝",
        "declension": "взял(а) за руку"
    },
    "подарить цветы": {
        "text": "{user1} подарил(а) букет алых роз {user2} 🌹",
        "emoji": "🌹",
        "declension": "подарил(а) цветы"
    },
    "сделать массаж": {
        "text": "{user1} сделал(а) расслабляющий массаж {user2} 💆",
        "emoji": "💆",
        "declension": "сделал(а) массаж"
    },
    "укутать": {
        "text": "{user1} заботливо укутал(а) в плед {user2} 🧶",
        "emoji": "🧶",
        "declension": "укутал(а)"
    },
    "позвать гулять": {
        "text": "{user1} позвал(а) на прогулку под луной {user2} 🌙",
        "emoji": "🌙",
        "declension": "позвал(а) гулять"
    },
    "сделать комплимент": {
        "text": "{user1} сказал(а) что-то очень приятное {user2} 🥰",
        "emoji": "🥰",
        "declension": "сделал(а) комплимент"
    },
    "посмотреть в глаза": {
        "text": "{user1} пристально посмотрел(а) в глаза {user2} 👀",
        "emoji": "👀",
        "declension": "посмотрел(а) в глаза"
    },
    "облить водой": {
        "text": "{user1} окатил(а) холодной водой {user2} 🚿",
        "emoji": "🚿",
        "declension": "облил(а) водой"
    },
    "напугать": {
        "text": "{user1} внезапно выскочил(а) и напугал(а) {user2} 👻",
        "emoji": "👻",
        "declension": "напугал(а)"
    },
    "поделиться едой": {
        "text": "{user1} отдал(а) свой последний кусочек {user2} 🍕",
        "emoji": "🍕",
        "declension": "поделился(ась) едой"
    },
    "подарить мишку": {
        "text": "{user1} подарил(а) плюшевого мишку {user2} 🧸",
        "emoji": "🧸",
        "declension": "подарил(а) мишку"
    },
    "облить": {
        "text": "{user1} облил(а) {user2} 💦",
        "emoji": "💦",
        "declension": "облил(а)"
    },
    "поделиться": {
        "text": "{user1} поделился(ась) с {user2} 🤝",
        "emoji": "🤝",
        "declension": "поделился(ась)"
    },
    "подарить": {
        "text": "{user1} сделал(а) подарок {user2} 🎁",
        "emoji": "🎁",
        "declension": "подарил(а)"
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

@router.message(lambda message: (message.text or message.caption) and any((message.text or message.caption).lower().strip().startswith(action) for action in SOCIAL_ACTIONS))
async def handle_social_action(message: types.Message):
    full_text = (message.text or message.caption).lower().strip()
    action_key = None
    
    # Сортируем ключи по длине, чтобы сначала проверялись более длинные (например "напоить водой")
    sorted_actions = sorted(SOCIAL_ACTIONS.keys(), key=len, reverse=True)
    
    for action in sorted_actions:
        if full_text.startswith(action):
            action_key = action
            break
            
    if not action_key:
        return

    # Извлекаем дополнение, если оно есть (например, в "ударить тапком" дополнение — "тапком")
    # Но для этого нам нужно знать, где заканчивается команда и начинается тег
    # В aiogram message.text может быть "ударить @user тапком" или "ударить тапком @user"
    
    target_user_id, command_args = await get_target_id(message, action_key)
    
    if not target_user_id:
        await message.reply(f"❌ Укажите, кого вы хотите {action_key} (тег или ответ на сообщение).")
        return
        
    if target_user_id == message.from_user.id:
        await message.reply(f"🤔 Вы пытаетесь {action_key} самого себя? Это как?")
        return

    user1_mention = await get_mention_by_id(message.from_user.id)
    user2_mention = await get_mention_by_id(target_user_id)
    
    # Проверяем, есть ли уже отношения
    rel_data = await get_relationship(message.from_user.id, target_user_id)
    
    action_info = SOCIAL_ACTIONS[action_key]
    
    # Если есть дополнительные слова в команде, строим динамический текст
    if command_args:
        declension = action_info.get("declension", action_key)
        emoji = action_info.get("emoji", "🔘")
        result_text = f"{user1_mention} {declension} {command_args} {user2_mention} {emoji}"
    else:
        result_text = action_info["text"].format(user1=user1_mention, user2=user2_mention)
    
    if rel_data:
        # Обновляем БД только если есть официальные отношения
        rel_data = await update_relationship(message.from_user.id, target_user_id, action_key)
        level = get_relationship_level(rel_data["total_interactions"])
        
        await message.answer(
            f"{result_text}\n\n"
            f"📊 <b>Отношения:</b> {level} (взаимодействий: {rel_data['total_interactions']})",
            parse_mode="HTML"
        )
    else:
        # Просто выводим текст действия, если отношений нет
        await message.answer(result_text, parse_mode="HTML")

@router.message(F.text.lower() == "наши отношения")
async def show_pair_relationships(message: types.Message):
    if not message.reply_to_message:
        await message.reply("❌ Ответьте на сообщение пользователя, чтобы посмотреть ваши отношения с ним.")
        return
        
    target_id = message.reply_to_message.from_user.id
    if target_id == message.from_user.id:
        await message.reply("🤡 Отношения с самим собой всегда прекрасны!")
        return
        
    rel_data = await get_relationship(message.from_user.id, target_id)
    target_mention = await get_mention_by_id(target_id)
    
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
    relationships = await get_all_user_relationships(message.from_user.id)
    
    if not relationships:
        await message.reply("👀 У вас пока нет истории отношений с кем-либо. Попробуйте обнять или поцеловать кого-нибудь!")
        return
        
    response = "📊 <b>Ваши отношения:</b>\n"
    response += "➖➖➖➖➖➖➖➖➖➖\n"
    
    # Показываем топ-10 отношений
    for i, rel in enumerate(relationships[:10], 1):
        partner_mention = await get_mention_by_id(rel["partner_id"])
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

    user1_mention = await get_mention_by_id(message.from_user.id)
    user2_mention = await get_mention_by_id(target_user_id)
    
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
        
    user1_mention = await get_mention_by_id(callback_data.user1_id)
    user2_mention = await get_mention_by_id(callback_data.user2_id)
    
    if callback_data.action == "accept":
        # Инициализируем отношения, если их нет (первое действие "начало")
        await update_relationship(callback_data.user1_id, callback_data.user2_id, "начало")
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
        
    rel_data = await get_relationship(message.from_user.id, target_id)
    if not rel_data:
        await message.reply("🤷‍♂️ У вас и так нет истории отношений с этим пользователем.")
        return
        
    await delete_relationship(message.from_user.id, target_id)
    target_mention = await get_mention_by_id(target_id)
    
    await message.reply(
        f"💔 Отношения с {target_mention} были разорваны. Вся история взаимодействий удалена.",
        parse_mode="HTML"
    )
