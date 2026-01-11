from aiogram import Router, types, F
from aiogram.enums import MessageEntityType
from bot.modules.bans import ban_user, unban_user
from bot.modules.mutes import mute_user, unmute_user
from bot.modules.warns import warn_user, list_warns, unwarn_user, clear_user_warns, remove_warn_index
from bot.modules.awards import give_award, remove_award_index
from bot.modules.moderation import delete_messages
from bot.utils.time_parser import parse_duration
from bot.utils.filters import AdminFilter, RankFilter
from bot.utils.db_manager import (
    get_user_id_by_username, get_mention_by_id, 
    update_user_cache, can_user_modify_other, get_user_rank_context
)
from bot.config_reader import config
from bot.keyboards.moderation_keyboards import ModAction
import re
import logging

router = Router()

# Фильтр для проверки, что команда отправлена в группе или супергруппе
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

async def get_target_id(message: types.Message, command_name: str):
    """
    Универсальная функция для поиска ID пользователя/бота в сообщении.
    """
    target_user_id = None
    command_args = message.text[len(command_name):].strip()

    # 1. Ответ на сообщение
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        await update_user_cache(target_user.id, target_user.username, target_user.full_name)
        return target_user.id, command_args

    # 2. Поиск в сущностях (упоминания)
    if message.entities:
        for entity in message.entities:
            if entity.type == MessageEntityType.TEXT_MENTION and entity.user:
                target_user = entity.user
                await update_user_cache(target_user.id, target_user.username, target_user.full_name)
                return target_user.id, command_args.replace(message.text[entity.offset:entity.offset+entity.length], "").strip()
            
            if entity.type == MessageEntityType.MENTION:
                mention_text = message.text[entity.offset:entity.offset+entity.length]
                # Проверяем кэш
                cached_id = await get_user_id_by_username(mention_text)
                if cached_id:
                    return cached_id, command_args.replace(mention_text, "").strip()
                
                # Прямой запрос (для публичных юзеров и ботов)
                try:
                    chat = await message.bot.get_chat(mention_text)
                    await update_user_cache(chat.id, chat.username, chat.full_name or chat.title)
                    return chat.id, command_args.replace(mention_text, "").strip()
                except Exception:
                    pass

    # 3. Поиск ID (цифры) в тексте
    id_match = re.search(r'(\d{5,15})', command_args)
    if id_match:
        found_id = int(id_match.group(1))
        return found_id, command_args.replace(id_match.group(1), "").strip()

    return None, command_args

@router.message(F.text.lower().startswith("бан"), RankFilter(min_rank=3))
async def handle_ban_command(message: types.Message):
    # Проверка прав самого бота
    bot_member = await message.chat.get_member(message.bot.id)
    if not bot_member.status in ["administrator", "creator"]:
        await message.reply("❌ Я не могу банить пользователей, так как я не администратор в этом чате.")
        return

    target_user_id, command_args = await get_target_id(message, "бан")

    if not target_user_id:
        await message.reply("❌ Не удалось найти пользователя. Убедитесь, что тег верный или используйте ID/ответ на сообщение.")
        return

    duration = None
    reason = "Не указана"

    # Парсинг времени
    duration_match = re.search(r'\b(\d+[мчд])\b', command_args)
    if duration_match:
        duration_str = duration_match.group(1)
        duration = parse_duration(duration_str)
        command_args = command_args.replace(duration_str, '', 1).strip()

    # Ограничения по рангам
    admin_rank, _, is_admin_super = await get_user_rank_context(message.from_user.id, message.chat)
    
    # Модератор (3) может банить максимум на 3 дня
    if admin_rank == 3:
        if not duration or duration.total_seconds() > 3 * 24 * 3600:
            await message.reply("⚠️ Модератор может банить максимум на 3 дня. Установите срок, например: <code>бан @тег 3д причина</code>", parse_mode="HTML")
            return
    
    # Проверка иерархии
    if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
        target_mention = await get_mention_by_id(target_user_id)
        await message.reply(f"❌ Вы не можете применить это действие к пользователю {target_mention} (иерархия).", parse_mode="HTML")
        return

    if command_args:
        reason = command_args

    await ban_user(message, target_user_id, duration, reason)

@router.message(F.text.lower().startswith("разбан"), RankFilter(min_rank=3))
async def handle_unban_command(message: types.Message):
    bot_member = await message.chat.get_member(message.bot.id)
    if not bot_member.status in ["administrator", "creator"]:
        await message.reply("❌ Я не администратор и не могу управлять списком разбана.")
        return

    target_user_id, _ = await get_target_id(message, "разбан")

    if not target_user_id:
        await message.reply("❌ Не удалось найти пользователя. Убедитесь, что тег верный или используйте ID/ответ на сообщение.")
        return

    await unban_user(message, target_user_id)

@router.message(F.text.lower().startswith("мут"), RankFilter(min_rank=3))
async def handle_mute_command(message: types.Message):
    """
    Обработчик команды 'мут'.
    """
    # Проверка прав бота
    bot_member = await message.chat.get_member(message.bot.id)
    if not bot_member.status in ["administrator", "creator"] or not bot_member.can_restrict_members:
        await message.reply("❌ Я не могу мутить пользователей. Убедитесь, что я администратор с правом ограничения участников.")
        return

    target_user_id, command_args = await get_target_id(message, "мут")
    
    if not target_user_id:
        await message.reply("❌ Не удалось найти пользователя. Убедитесь, что тег верный или используйте ID/ответ на сообщение.")
        return

    # Проверка иерархии
    if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
        target_mention = await get_mention_by_id(target_user_id)
        await message.reply(f"❌ Вы не можете применить это действие к пользователю {target_mention} (иерархия).", parse_mode="HTML")
        return
        
    await mute_user(message, target_user_id, command_args)

@router.message(F.text.lower().startswith("кик"), RankFilter(min_rank=4))
async def handle_kick_command(message: types.Message):
    """
    Обработчик команды 'кик'.
    """
    # Проверка прав бота
    bot_member = await message.chat.get_member(message.bot.id)
    if not bot_member.status in ["administrator", "creator"] or not bot_member.can_restrict_members:
        await message.reply("❌ Я не могу кикать пользователей. Убедитесь, что я администратор.")
        return

    target_user_id, _ = await get_target_id(message, "кик")
    
    if not target_user_id:
        await message.reply("❌ Не удалось найти пользователя. Убедитесь, что тег верный или используйте ID/ответ на сообщение.")
        return

    # Проверка иерархии
    if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
        target_mention = await get_mention_by_id(target_user_id)
        await message.reply(f"❌ Вы не можете применить это действие к пользователю {target_mention} (иерархия).", parse_mode="HTML")
        return

    try:
        # Кик в Telegram (бан и сразу разбан)
        await message.chat.ban(target_user_id)
        await message.chat.unban(target_user_id)
        
        target_mention = await get_mention_by_id(target_user_id)
        await message.reply(f"👞 Пользователь {target_mention} был <b>кикнут</b> из группы.", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка при кике: {e}")
        await message.reply("❌ Не удалось кикнуть пользователя. Возможно, у меня недостаточно прав или пользователь является администратором Telegram.")

@router.message(F.text.lower().startswith("размут"), RankFilter(min_rank=3))
async def handle_unmute_command(message: types.Message):
    """
    Обработчик команды 'размут'.
    """
    # Проверка прав бота
    bot_member = await message.chat.get_member(message.bot.id)
    if not bot_member.status in ["administrator", "creator"] or not bot_member.can_restrict_members:
        await message.reply("❌ Я не могу размучивать пользователей. Убедитесь, что я администратор с правом ограничения участников.")
        return

    target_user_id, _ = await get_target_id(message, "размут")
    
    if not target_user_id:
        await message.reply("❌ Не удалось найти пользователя. Убедитесь, что тег верный или используйте ID/ответ на сообщение.")
        return
        
    await unmute_user(message, target_user_id)

@router.message(F.text.lower().startswith("варн"), RankFilter(min_rank=2))
async def handle_warn_command(message: types.Message):
    """
    Обработчик команды 'варн' и 'варны'.
    """
    text = message.text.lower().strip()
    
    # Если команда 'варны' (просмотр списка)
    if text.startswith("варны"):
        target_user_id, _ = await get_target_id(message, "варны")
        if not target_user_id:
            await message.reply("❌ Не удалось найти пользователя. Убедитесь, что тег верный или используйте ID/ответ на сообщение.")
            return
        await list_warns(message, target_user_id)
        return

    # Иначе это команда 'варн' (выдача предупреждения)
    target_user_id, command_args = await get_target_id(message, "варн")
    
    if not target_user_id:
        await message.reply("❌ Не удалось найти пользователя. Убедитесь, что тег верный или используйте ID/ответ на сообщение.")
        return

    # Проверка иерархии
    if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
        target_mention = await get_mention_by_id(target_user_id)
        await message.reply(f"❌ Вы не можете применить это действие к пользователю {target_mention} (иерархия).", parse_mode="HTML")
        return
        
    await warn_user(message, target_user_id, command_args)

@router.message(F.text.lower().startswith("разварн"), RankFilter(min_rank=2))
async def handle_unwarn_command(message: types.Message):
    """
    Обработчик команды 'разварн'.
    """
    target_user_id, _ = await get_target_id(message, "разварн")
    
    if not target_user_id:
        await message.reply("❌ Не удалось найти пользователя. Убедитесь, что тег верный или используйте ID/ответ на сообщение.")
        return
        
    # Проверка иерархии
    if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
        target_mention = await get_mention_by_id(target_user_id)
        await message.reply(f"❌ Вы не можете изменять предупреждения пользователя {target_mention} (иерархия).", parse_mode="HTML")
        return

    await unwarn_user(message, target_user_id)

@router.message(F.text.lower().startswith("-варн"), RankFilter(min_rank=3))
async def handle_remove_warn_index_command(message: types.Message):
    """
    Обработчик команды '-варн @тег номер'.
    """
    text = message.text.lower().strip()
    
    # 1. Сначала пытаемся найти ID пользователя через универсальную функцию
    target_user_id, command_args = await get_target_id(message, "-варн")
    
    if not target_user_id:
        # Если не нашли через get_target_id, пробуем в ответе на сообщение
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        else:
            await message.reply("❌ Не удалось найти пользователя. Используйте: <code>-варн @тег номер</code> или ответ на сообщение.", parse_mode="HTML")
            return

    # 2. Теперь извлекаем номер варна из оставшихся аргументов
    # command_args содержит всё, что осталось после удаления команды и тега
    parts = command_args.split()
    if not parts:
        await message.reply("❌ Укажите номер варна. Пример: <code>-варн @тег 1</code>", parse_mode="HTML")
        return
    
    try:
        index = int(parts[0])
    except ValueError:
        await message.reply("❌ Номер варна должен быть числом.")
        return
            
    # Проверка иерархии
    if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
        target_mention = await get_mention_by_id(target_user_id)
        await message.reply(f"❌ Вы не можете изменять предупреждения пользователя {target_mention} (иерархия).", parse_mode="HTML")
        return

    await remove_warn_index(message, target_user_id, index)

@router.message(F.text.lower().startswith("-награда"), RankFilter(min_rank=5))
async def handle_remove_award_command(message: types.Message):
    """
    Обработчик команды '-награда @тег номер'.
    """
    target_user_id, command_args = await get_target_id(message, "-награда")
    
    if not target_user_id:
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        else:
            await message.reply("❌ Не удалось найти пользователя. Используйте: <code>-награда @тег номер</code>", parse_mode="HTML")
            return

    parts = command_args.split()
    if not parts:
        await message.reply("❌ Укажите номер награды. Пример: <code>-награда @тег 1</code>", parse_mode="HTML")
        return
    
    try:
        index = int(parts[0])
    except ValueError:
        await message.reply("❌ Номер награды должен быть числом.")
        return
            
    # Проверка иерархии
    if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
        target_mention = await get_mention_by_id(target_user_id)
        await message.reply(f"❌ Вы не можете удалять награды этого пользователя (иерархия).", parse_mode="HTML")
        return

    await remove_award_index(message, target_user_id, index)

@router.message(F.text.lower().startswith("выдать награду"), RankFilter(min_rank=3))
async def handle_give_award_command(message: types.Message):
    """
    Обработчик команды 'Выдать награду @тег текст'.
    """
    target_user_id, command_args = await get_target_id(message, "выдать награду")
    
    if not target_user_id:
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        else:
            await message.reply("❌ Не удалось найти пользователя. Используйте: <code>Выдать награду @тег текст</code>", parse_mode="HTML")
            return

    if not command_args:
        await message.reply("❌ Укажите текст награды!")
        return
        
    # Проверка иерархии
    admin_rank, _, is_admin_super = await get_user_rank_context(message.from_user.id, message.chat)
    
    # Логика: 5 ранг (Создатель/Супер) может давать награды всем, кроме самого себя.
    # Но если это Глобальный Создатель (из конфига), он может и себе.
    is_global_creator = config.creator_id and message.from_user.id == config.creator_id
    
    if message.from_user.id == target_user_id and not is_global_creator:
        await message.reply("❌ Вы не можете выдавать награду самому себе!")
        return

    # Если не 5 ранг и не глобальный создатель, проверяем обычную иерархию
    if admin_rank < 5 and not is_global_creator:
        if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
            target_mention = await get_mention_by_id(target_user_id)
            await message.reply(f"❌ Вы не можете выдавать награды этому пользователю (иерархия).", parse_mode="HTML")
            return

    await give_award(message, target_user_id, command_args)

@router.message(F.text.lower().startswith("очиститьварны"), RankFilter(min_rank=5))
async def handle_clear_warns_command(message: types.Message):
    """
    Обработчик команды 'очиститьварны'.
    """
    target_user_id, _ = await get_target_id(message, "очиститьварны")
    
    if not target_user_id:
        await message.reply("❌ Не удалось найти пользователя. Убедитесь, что тег верный или используйте ID/ответ на сообщение.")
        return
        
    # Проверка иерархии
    if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
        target_mention = await get_mention_by_id(target_user_id)
        await message.reply(f"❌ Вы не можете очистить варны пользователя {target_mention} (иерархия).", parse_mode="HTML")
        return

    await clear_user_warns(message, target_user_id)

@router.message(F.text.lower().startswith("удалить"), RankFilter(min_rank=3))
async def handle_delete_command(message: types.Message):
    # Проверка прав на удаление
    bot_member = await message.chat.get_member(message.bot.id)
    if not bot_member.status in ["administrator", "creator"]:
        await message.reply("❌ У меня нет прав на удаление сообщений.")
        return

    args_text = message.text.lower().replace("удалить", "", 1).strip()
    count = 1
    
    if args_text:
        try:
            count = int(args_text)
        except ValueError:
            await message.reply("❌ Укажите число сообщений для удаления.")
            return
    
    if count > 10:
        count = 10
        await message.reply("⚠️ Максимум 10 сообщений.")

    await delete_messages(message, count)

@router.callback_query(AdminFilter(), ModAction.filter(F.action == "unban"))
async def cb_unban_user(callback: types.CallbackQuery, callback_data: ModAction):
    """
    Обработка кнопки разблокировки из уведомления об автобане.
    """
    user_id = callback_data.user_id
    chat_id = callback.message.chat.id
    try:
        # Снимаем бан в Telegram
        await callback.bot.unban_chat_member(chat_id, user_id)
        
        # Удаляем из нашей базы
        from bot.utils.db_manager import remove_ban
        await remove_ban(chat_id, user_id)
        
        admin_name = callback.from_user.full_name
        await callback.message.edit_text(
            f"✅ Пользователь с ID <code>{user_id}</code> был разблокирован администратором {admin_name}.",
            parse_mode="HTML"
        )
        await callback.answer("Пользователь разблокирован")
    except Exception as e:
        logging.error(f"Ошибка при разблокировке через кнопку: {e}")
        await callback.answer("❌ Не удалось разблокировать пользователя", show_alert=True)

@router.callback_query(ModAction.filter(F.action == "delete_msg"))
async def cb_delete_msg(callback: types.CallbackQuery):
    """
    Обработка кнопки 'Убрать'.
    """
    try:
        await callback.message.delete()
    except Exception:
        await callback.answer("Не удалось удалить сообщение")
