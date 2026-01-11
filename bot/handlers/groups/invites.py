from aiogram import Router, types, F
from bot.utils.db_manager import get_inviter, get_mention_by_id, update_user_cache

router = Router()

@router.message(F.text.lower().in_(["кто тебя пригласил", "кто тебя добавил", "кто пригласил", "кто добавил"]))
async def handle_who_invited_command(message: types.Message):
    """
    Обработчик команды 'кто тебя пригласил' / 'кто тебя добавил'.
    Работает как ответом на сообщение, так и просто в чате (для отправителя).
    """
    # Определяем цель (тот, о ком спрашиваем)
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        target_user = message.from_user
        
    # Обновляем кэш для целевого пользователя, так как мы его точно видим сейчас
    update_user_cache(target_user.id, target_user.username, target_user.full_name)
    
    inviter_id = get_inviter(message.chat.id, target_user.id)
    target_mention = get_mention_by_id(target_user.id)
    
    if inviter_id is None:
        await message.reply(
            f"❓ К сожалению, у меня нет данных о том, кто пригласил {target_mention}. "
            f"(Данные собираются только для новых участников)",
            parse_mode="HTML"
        )
        return
        
    if inviter_id == "link":
        await message.reply(
            f"🔗 Пользователь {target_mention} зашел в группу самостоятельно по ссылке.",
            parse_mode="HTML"
        )
    else:
        # Пытаемся получить информацию об пригласителе из чата, если её нет в кэше
        inviter_mention = get_mention_by_id(inviter_id)
        if "пользователь" in inviter_mention.lower():
            try:
                member = await message.chat.get_member(user_id=int(inviter_id))
                if member and member.user:
                    update_user_cache(member.user.id, member.user.username, member.user.full_name)
                    inviter_mention = get_mention_by_id(inviter_id)
            except Exception:
                pass
                
        await message.reply(
            f"👤 Пользователя {target_mention} пригласил {inviter_mention}.",
            parse_mode="HTML"
        )
