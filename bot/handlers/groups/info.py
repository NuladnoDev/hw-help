import random
from aiogram import Router, types, F
from bot.utils.filters import ModuleEnabledFilter

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("info"))

@router.message(F.text.regexp(r"(?i)^!?инфа\b"))
async def handle_info(message: types.Message):
    """Выдает рандомный шанс информации."""
    # Убираем команду из текста
    text = message.text
    if text.startswith("!"):
        text = text[1:]
    
    # Ищем саму фразу после "инфа"
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❓ Укажите текст для проверки вероятности.\nПример: <code>!инфа я сегодня разбогатею</code>", parse_mode="HTML")
        return
        
    chance = random.randint(0, 100)
    await message.reply(f"📊 Вероятность составляет: <b>{chance}%</b>", parse_mode="HTML")
