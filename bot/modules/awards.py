from aiogram import types
from bot.utils.db_manager import add_award, remove_award_by_index, get_mention_by_id, get_user_mention_with_nickname

async def give_award(message: types.Message, target_user_id: int, text: str):
    """
    Выдает награду пользователю.
    """
    if target_user_id == message.from_user.id:
        await message.reply("❌ Вы не можете выдать награду самому себе!")
        return
    
    if not text:
        await message.reply("❌ Вы не указали текст награды!")
        return
        
    add_award(message.chat.id, target_user_id, message.from_user.id, text)
    
    target_mention = get_mention_by_id(target_user_id)
    admin_mention = get_user_mention_with_nickname(message.from_user)
    
    await message.answer(
        f"🏆 {admin_mention} выдал награду {target_mention}\n"
        f"Текст: {text}",
        parse_mode="HTML"
    )

async def remove_award_index(message: types.Message, target_user_id: int, index: int):
    """
    Удаляет награду по индексу.
    """
    target_mention = get_mention_by_id(target_user_id)
    if remove_award_by_index(message.chat.id, target_user_id, index - 1):
        await message.answer(f"✅ Награда №{index} для {target_mention} удалена.", parse_mode="HTML")
    else:
        await message.answer(f"❌ Не удалось найти награду №{index} для {target_mention}.", parse_mode="HTML")
