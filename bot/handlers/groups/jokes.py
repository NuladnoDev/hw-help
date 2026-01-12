from aiogram import Router, types, F
from bot.utils.joke_api import get_random_joke
from bot.utils.filters import ModuleEnabledFilter

router = Router()
# Фильтр для групп и включенного модуля "jokes"
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("jokes"))

@router.message(F.text.lower() == "анекдот")
async def handle_joke_command(message: types.Message):
    """Отправляет случайный анекдот."""
    joke = await get_random_joke()
    await message.reply(joke)
