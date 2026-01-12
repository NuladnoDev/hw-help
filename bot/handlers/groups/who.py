import random
from aiogram import Router, types, F
from bot.utils.db_manager import get_chat_user_ids, get_mention_by_id
from bot.utils.filters import ModuleEnabledFilter

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("who"))

@router.message(F.text.regexp(r"(?i)^!?кто\b"))
async def handle_who(message: types.Message):
    """Выбирает случайного пользователя."""
    user_ids = await get_chat_user_ids(message.chat.id)
    
    if not user_ids:
        await message.reply("❌ В этом чате нет активных пользователей.")
        return
        
    winner_id = random.choice(user_ids)
    mention = await get_mention_by_id(winner_id)
    
    # Извлекаем текст после команды
    text = message.text
    if text.startswith("!"):
        text = text[1:]
        
    parts = text.split(maxsplit=1)
    action = parts[1] if len(parts) > 1 else "этот человек"
    
    await message.answer(f"🔎 Я думаю, что {action} — это {mention}", parse_mode="HTML")
