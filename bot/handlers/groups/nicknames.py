from aiogram import Router, types, F
from bot.utils.db_manager import set_nickname, remove_nickname, get_mention_by_id
from bot.handlers.groups.moderation import get_target_id
import logging

router = Router()

# Фильтр для проверки, что событие произошло в группе или супергруппе
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(F.text.lower().startswith("+ник"))
async def handle_set_nickname_command(message: types.Message):
    """
    Команда '+Ник (никнейм)'
    Устанавливает глобальный никнейм для пользователя.
    """
    # Используем оригинальный текст для сохранения регистра никнейма, 
    # но проверяем команду в нижнем регистре
    text = message.text
    if text.lower().startswith("+ник"):
        nickname = text[4:].strip()
    else:
        return # На всякий случай

    if not nickname:
        await message.reply("❌ Вы не указали никнейм. Пример: <code>+Ник СуперГерой</code>", parse_mode="HTML")
        return

    if len(nickname) > 32:
        await message.reply("❌ Никнейм слишком длинный (максимум 32 символа).")
        return

    set_nickname(message.from_user.id, nickname)
    await message.reply(f"✅ Теперь во всех группах я буду называть вас: <b>{nickname}</b>", parse_mode="HTML")

@router.message(F.text.lower().startswith("-ник"))
async def handle_remove_nickname_command(message: types.Message):
    """
    Команда '-Ник'
    Удаляет глобальный никнейм пользователя.
    """
    if remove_nickname(message.from_user.id):
        await message.reply("✅ Ваш никнейм удален. Теперь я буду использовать ваше стандартное имя.")
    else:
        await message.reply("❌ у вас и так нет кастомного никнейма.")

@router.message(F.text.lower().startswith(("назначить ник", "назначить никнейм", "назначить имя")))
async def handle_set_nickname_other(message: types.Message):
    """
    Обработчик команд 'Назначить ник/никнейм/имя @тег ник'.
    Позволяет администраторам (или всем, согласно текущей логике) менять ники другим.
    """
    text = message.text.lower()
    command = ""
    if text.startswith("назначить никнейм"):
        command = "назначить никнейм"
    elif text.startswith("назначить имя"):
        command = "назначить имя"
    else:
        command = "назначить ник"

    target_user_id, command_args = await get_target_id(message, command)
    
    if not target_user_id:
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        else:
            await message.reply(f"❌ Не удалось найти пользователя. Используйте: <code>{command} @тег ник</code>", parse_mode="HTML")
            return

    if not command_args:
        await message.reply("❌ Вы не указали новый никнейм!")
        return
        
    new_nickname = command_args.strip()
    if len(new_nickname) > 32:
        await message.reply("❌ Никнейм слишком длинный (максимум 32 символа).")
        return
        
    set_nickname(target_user_id, new_nickname)
    target_mention = get_mention_by_id(target_user_id)
    await message.reply(f"✅ Для пользователя {target_mention} установлен никнейм: {new_nickname}", parse_mode="HTML")
