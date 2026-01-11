from aiogram import Router, types, F
from bot.utils.db_manager import (
    is_user_banned, is_user_muted, update_user_cache, 
    get_user_mention_with_nickname, update_user_activity, save_inviter
)
from bot.keyboards.moderation_keyboards import get_auto_ban_kb
import logging

router = Router()

# Фильтр для проверки, что событие произошло в группе или супергруппе
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(F.new_chat_members)
async def on_user_join(message: types.Message):
    """
    Срабатывает, когда пользователь вступает в чат или его приглашают.
    """
    bot_info = await message.bot.get_me()
    for user in message.new_chat_members:
        # Проверяем, не сам ли это бот
        if user.id == bot_info.id:
            await message.answer(
                "Я рад, что меня добавили.\n"
                "Назначьте бота администратором группы"
            )
            continue

        # Кэшируем новичка
        update_user_cache(user.id, user.username, user.full_name)
        
        # Кэшируем пригласившего (если это не сам пользователь)
        if message.from_user and message.from_user.id != user.id:
            update_user_cache(message.from_user.id, message.from_user.username, message.from_user.full_name)
        
        # Сохраняем, кто пригласил
        inviter_id = message.from_user.id if message.from_user and message.from_user.id != user.id else "link"
        save_inviter(message.chat.id, user.id, inviter_id)
        
        if is_user_banned(message.chat.id, user.id):
            try:
                # Перебаниваем пользователя
                await message.chat.ban(user_id=user.id)
                user_mention = get_user_mention_with_nickname(user)
                await message.answer(
                    f"⚠️ Внимание! {user_mention} (ID: <code>{user.id}</code>) "
                    f"был забанен ранее и возвращен в бан-лист автоматически.",
                    parse_mode="HTML",
                    reply_markup=get_auto_ban_kb(user.id)
                )
            except Exception as e:
                logging.error(f"Ошибка при автоматическом перебане {user.id}: {e}")
        
        elif is_user_muted(message.chat.id, user.id):
            try:
                # Накладываем мут повторно
                permissions = types.ChatPermissions(can_send_messages=False)
                await message.chat.restrict(user_id=user.id, permissions=permissions)
                user_mention = get_user_mention_with_nickname(user)
                await message.answer(
                    f"🤐 {user_mention} вернулся, но его мут ещё не истек. Права ограничены автоматически.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Ошибка при автоматическом муте {user.id}: {e}")

@router.message(F.left_chat_member)
async def on_user_leave(message: types.Message):
    """
    Срабатывает, когда пользователь покидает чат.
    """
    # Здесь можно добавить логику, если нужно
    pass

@router.message()
async def silent_handler(message: types.Message):
    """
    Пустой хендлер для того, чтобы обычные сообщения считались 'обработанными'
    и не забивали логи ошибкой 'Update is not handled'.
    """
    pass
