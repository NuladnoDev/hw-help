import time
from aiogram import Router, types, F
from bot.utils.filters import ModuleEnabledFilter

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("ping"))

@router.message(F.text.regexp(r"(?i)^!?пинг\b"))
async def handle_ping(message: types.Message):
    """Проверяет пинг бота."""
    start_time = time.time()
    sent_message = await message.answer("📡 Проверяю связь...")
    end_time = time.time()
    
    ping = round((end_time - start_time) * 1000)
    await sent_message.edit_text(f"✅ На месте!\n⏱ Пинг: <code>{ping} мс</code>", parse_mode="HTML")
