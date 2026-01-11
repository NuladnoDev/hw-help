from aiogram import Router, types, F
from aiogram.filters import CommandStart
from bot.keyboards.user_keyboards import get_start_kb

router = Router()

@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: types.Message):
    bot_info = await message.bot.get_me()
    welcome_text = (
        f"👋 *Привет! Я — HW-Help Bot.*\n\n"
        f"🤖 Я помогу вам управлять вашим чатом: модерировать сообщения, настраивать ранги и развлекать участников.\n\n"
        f"📍 Чтобы начать использовать меня, добавьте бота в свою группу и выдайте права администратора."
    )
    
    await message.answer(
        text=welcome_text,
        reply_markup=get_start_kb(bot_info.username),
        parse_mode="Markdown"
    )
