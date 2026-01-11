import random
import asyncio
from aiogram import Router, types, F
from bot.utils.db_manager import get_mention_by_id

router = Router()

@router.message(F.text.lower() == "русская рулетка")
async def handle_roulette_command(message: types.Message):
    """Игра в русскую рулетку."""
    user_mention = get_mention_by_id(message.from_user.id)
    
    # Эффект ожидания
    msg = await message.answer(f"🔫 {user_mention} приставляет револьвер к виску и нажимает на курок...", parse_mode="HTML")
    await asyncio.sleep(1.5)
    
    # Логика (шанс 1/6)
    if random.randint(1, 6) == 1:
        await msg.edit_text(
            f"💥 БАХ! {user_mention} застрелился. Удача сегодня не на твоей стороне.\n\n"
            f"Чтобы испытать удачу ещё раз снова введите Русская рулетка.",
            parse_mode="HTML"
        )
    else:
        await msg.edit_text(
            f"💨 Щелчок... {user_mention} выжил! В барабане было пусто.\n\n"
            f"Чтобы испытать удачу ещё раз снова введите Русская рулетка.",
            parse_mode="HTML"
        )
