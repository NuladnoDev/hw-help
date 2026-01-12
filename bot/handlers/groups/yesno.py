import random
from aiogram import Router, types, F
from bot.utils.filters import ModuleEnabledFilter

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("yesno"))

@router.message(F.text.regexp(r"(?i)^!?данет\b"))
async def handle_yesno(message: types.Message):
    """Выбирает да или нет."""
    answer = random.choice(["Да", "Нет"])
    await message.reply(answer)
