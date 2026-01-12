from aiogram import Router, types, F
from bot.utils.filters import ModuleEnabledFilter

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("repeat"))

@router.message(F.text.lower().startswith("повтори"))
async def handle_repeat(message: types.Message):
    """Повторяет текст пользователя."""
    command_len = len("повтори")
    text_to_repeat = message.text[command_len:].strip()
    
    if not text_to_repeat:
        await message.reply("❌ Напишите текст, который я должен повторить.\nПример: <code>Повтори я люблю ботов</code>", parse_mode="HTML")
        return
    
    try:
        await message.delete()
    except Exception:
        pass
        
    await message.answer(text_to_repeat)
