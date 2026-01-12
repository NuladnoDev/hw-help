import random
import re
from aiogram import Router, types, F
from bot.utils.filters import ModuleEnabledFilter

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("choose"))

@router.message(F.text.regexp(r"(?i)^!?выбери\b"))
async def handle_choose(message: types.Message):
    """Выбирает один из предложенных вариантов."""
    text = message.text
    if text.startswith("!"):
        text = text[1:]
        
    # Убираем само слово "выбери"
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❓ Укажите варианты через пробел или запятую.\nПример: <code>!выбери чай кофе сок</code>", parse_mode="HTML")
        return
        
    options_text = parts[1]
    # Разбиваем по запятым или пробелам
    options = [opt.strip() for opt in re.split(r"[,|\s]+", options_text) if opt.strip()]
    
    if len(options) < 2:
        await message.reply("❓ Нужно хотя бы два варианта для выбора.")
        return
        
    choice = random.choice(options)
    await message.reply(f"🤔 Я выбираю: <b>{choice}</b>", parse_mode="HTML")
