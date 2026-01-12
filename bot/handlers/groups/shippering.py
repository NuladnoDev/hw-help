import random
from aiogram import Router, types, F
from bot.utils.db_manager import get_chat_user_ids, get_mention_by_id
from bot.utils.filters import ModuleEnabledFilter

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("shippering"))

@router.message(F.text.lower() == "шипперинг")
async def handle_shippering(message: types.Message):
    """Шипперит двух случайных участников чата."""
    user_ids = await get_chat_user_ids(message.chat.id)
    
    if len(user_ids) < 2:
        await message.reply("❌ В этом чате слишком мало активных пользователей для шипперинга.")
        return
    
    pair = random.sample(user_ids, 2)
    user1_mention = await get_mention_by_id(pair[0])
    user2_mention = await get_mention_by_id(pair[1])
    
    love_percent = random.randint(0, 100)
    
    if love_percent < 20:
        emoji = "🙊"
    elif love_percent < 50:
        emoji = "😏"
    elif love_percent < 80:
        emoji = "❤️"
    else:
        emoji = "💍"
    
    text = (
        f"💞 <b>Шипперинг тайм!</b>\n\n"
        f"Сегодня лучшая пара чата:\n"
        f"{user1_mention} + {user2_mention} = <b>{love_percent}%</b> {emoji}"
    )
    
    await message.answer(text, parse_mode="HTML")
