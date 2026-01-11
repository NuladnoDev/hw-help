from aiogram import Router, types, F
from bot.modules.profile import get_user_profile
from bot.utils.db_manager import (
    set_rank, get_rank, get_mention_by_id, RANKS, 
    get_all_ranked_users, get_user_rank_context, can_user_modify_other,
    set_group_rank_names, get_group_rank_name
)
from bot.handlers.groups.moderation import get_target_id
from bot.utils.filters import AdminFilter, RankFilter
from bot.config_reader import config
import re

router = Router()

# Фильтр для проверки, что событие произошло в группе или супергруппе
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(F.text.lower().in_({"помощь", "/help"}))
async def handle_help_command(message: types.Message):
    """
    Выводит информационное сообщение со ссылками на обучающие статьи.
    """
    help_text = (
        "<b>📚 Центр помощи HW-Help</b>\n\n"
        "Здесь собраны инструкции по использованию бота:\n\n"
        "• Помощь по командам — <a href='https://telegra.ph/Pomoshch-po-komandam-01-11'>Статья</a>\n"
        "<i>Список будет дополняться по мере появления новых функций.</i>"
    )
    try:
        await message.reply(help_text, parse_mode="HTML", disable_web_page_preview=False)
    except Exception:
        # Если превью вызывает ошибку, шлем без него
        await message.reply(help_text, parse_mode="HTML", disable_web_page_preview=True)

def parse_rank_level(args_str):
    """Парсит уровень ранга из строки аргументов."""
    match = re.search(r'(\d+)', args_str)
    if match:
        return int(match.group(1))
    return None

@router.message(F.text.lower().startswith("назначить"), RankFilter(min_rank=5))
async def handle_set_rank_command(message: types.Message):
    target_user_id, command_args = await get_target_id(message, "назначить")
    
    if not target_user_id:
        await message.reply("❌ Не удалось найти пользователя. Используйте: <code>Назначить уровень @тег</code>", parse_mode="HTML")
        return

    # Проверка иерархии
    if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
        await message.reply("❌ Вы не можете изменять ранг этого пользователя (иерархия).", parse_mode="HTML")
        return

    rank_level = parse_rank_level(command_args)
    if rank_level is None:
        ranks_list = "\n".join([f"{level} - {name}" for level, name in RANKS.items()])
        await message.reply(f"❌ Укажите уровень ранга.\nДоступные ранги:\n{ranks_list}")
        return
        
    if rank_level not in RANKS:
        await message.reply(f"❌ Неверный уровень ранга. Доступно от 1 до {max(RANKS.keys())}.")
        return
    
    current_rank_user, _, is_current_super = await get_user_rank_context(message.from_user.id, message.chat)
    # Нельзя назначить ранг выше своего (для не супер-админов)
    if not is_current_super and rank_level >= current_rank_user:
        await message.reply(f"❌ Вы не можете назначить ранг {rank_level}, так как ваш ранг {current_rank_user}.")
        return
        
    if await set_rank(target_user_id, message.chat.id, rank_level):
        target_mention = await get_mention_by_id(target_user_id)
        rank_name = await get_group_rank_name(message.chat.id, rank_level, "nom")
        await message.reply(f"✅ Для пользователя {target_mention} установлен ранг: <b>{rank_name}</b> [{rank_level}]", parse_mode="HTML")
    else:
        await message.reply("❌ Произошла ошибка при сохранении ранга.")

@router.message(F.text.lower().startswith("повысить"), RankFilter(min_rank=5))
async def handle_promote_rank_command(message: types.Message):
    target_user_id, command_args = await get_target_id(message, "повысить")
    
    if not target_user_id:
        await message.reply("❌ Не удалось найти пользователя. Используйте: <code>Повысить [уровень] @тег</code>", parse_mode="HTML")
        return

    # Проверка иерархии
    if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
        await message.reply("❌ Вы не можете повышать этого пользователя (иерархия).", parse_mode="HTML")
        return

    current_rank_user, _, is_current_super = await get_user_rank_context(message.from_user.id, message.chat)
    current_level, _, _ = await get_user_rank_context(target_user_id, message.chat)
    new_level = parse_rank_level(command_args)
    
    if new_level is None:
        new_level = current_level + 1
    
    if new_level > max(RANKS.keys()):
        await message.reply(f"❌ Нельзя повысить выше {max(RANKS.keys())} ранга.")
        return

    if new_level <= current_level and command_args:
        await message.reply(f"❌ Указанный ранг ({new_level}) не выше текущего ({current_level}).")
        return

    if not is_current_super and new_level >= current_rank_user:
        await message.reply(f"❌ Вы не можете повысить до ранга {new_level}, так как ваш ранг {current_rank_user}.")
        return

    if await set_rank(target_user_id, message.chat.id, new_level):
        target_mention = await get_mention_by_id(target_user_id)
        rank_name = await get_group_rank_name(message.chat.id, new_level, "nom")
        await message.reply(f"✅ Для пользователя {target_mention} установлен ранг: <b>{rank_name}</b> [{new_level}]", parse_mode="HTML")
    else:
        await message.reply("❌ Произошла ошибка при сохранении ранга.")

@router.message(F.text.lower().startswith("понизить"), RankFilter(min_rank=5))
async def handle_demote_rank_command(message: types.Message):
    target_user_id, command_args = await get_target_id(message, "понизить")
    
    if not target_user_id:
        await message.reply("❌ Не удалось найти пользователя. Используйте: <code>Понизить [уровень] @тег</code>", parse_mode="HTML")
        return

    # Проверка иерархии
    if not await can_user_modify_other(message.from_user.id, target_user_id, message.chat):
        await message.reply("❌ Вы не можете понижать этого пользователя (иерархия).", parse_mode="HTML")
        return

    current_rank_user, _, is_current_super = await get_user_rank_context(message.from_user.id, message.chat)
    current_level, _, _ = await get_user_rank_context(target_user_id, message.chat)
    new_level = parse_rank_level(command_args)
    
    if new_level is None:
        new_level = current_level - 1
    
    if new_level < 1:
        await message.reply("❌ Нельзя понизить ниже 1 ранга.")
        return

    if new_level >= current_level and command_args:
        await message.reply(f"❌ Указанный ранг ({new_level}) не ниже текущего ({current_level}).")
        return

    if await set_rank(target_user_id, message.chat.id, new_level):
        target_mention = await get_mention_by_id(target_user_id)
        rank_name = await get_group_rank_name(message.chat.id, new_level, "nom")
        await message.reply(f"✅ Для пользователя {target_mention} установлен ранг: <b>{rank_name}</b> [{new_level}]", parse_mode="HTML")
    else:
        await message.reply("❌ Произошла ошибка при сохранении ранга.")

@router.message(lambda message: (message.text or message.caption or "").lower().startswith(("разжаловать", "снять")))
async def handle_strip_rank_command(message: types.Message):
    """Понижает ранг пользователя до 0."""
    command_name = "разжаловать" if (message.text or message.caption or "").lower().startswith("разжаловать") else "снять"
    
    target_id, _ = await get_target_id(message, command_name)
    if not target_id:
        await message.reply("❓ Кого нужно разжаловать? Ответьте на сообщение или введите ID/username.")
        return

    admin_id = message.from_user.id
    admin_rank = await get_rank(admin_id, message.chat.id)
    target_rank = await get_rank(target_id, message.chat.id)

    # Проверка прав (только вышестоящие могут разжаловать)
    if admin_rank <= target_rank and admin_id not in [6363065403, 1011831818]:
        await message.reply("🚫 У вас недостаточно прав для разжалования этого пользователя.")
        return

    if target_rank == 0:
        await message.reply("ℹ️ У пользователя уже минимальный ранг.")
        return

    success = await set_rank(target_id, message.chat.id, 0)
    if success:
        target_mention = await get_mention_by_id(target_id)
        rank_name = await get_group_rank_name(message.chat.id, 0, "nom")
        await message.reply(f"✅ Пользователь {target_mention} был разжалован до ранга: <b>{rank_name}</b>", parse_mode="HTML")
    else:
        await message.reply("❌ Произошла ошибка при разжаловании пользователя.")

@router.message(F.text.lower().regexp(r'^(кто ты|ты кто|профиль)'))
async def handle_who_are_you_command(message: types.Message):
    """Выводит профиль указанного пользователя или отправителя."""
    text = message.text.lower()
    command_name = ""
    if text.startswith("кто ты"):
        command_name = "кто ты"
    elif text.startswith("ты кто"):
        command_name = "ты кто"
    elif text.startswith("профиль"):
        command_name = "профиль"
        
    target_user_id, _ = await get_target_id(message, command_name)
    
    # Если цель не указана и нет реплая, проверяем отправителя
    if not target_user_id:
        target_user_id = message.from_user.id
        
    await get_user_profile(message, target_user_id)

@router.message(F.text.lower().startswith("ранг"), RankFilter(min_rank=5))
async def handle_set_custom_rank_name_command(message: types.Message):
    """
    Устанавливает кастомные названия для ранга в группе.
    Формат: Ранг 1 = Мишки мишек мишкой
    """
    pattern = r"^ранг\s+(\d+)\s*=\s*(\w+)\s+(\w+)\s+(\w+)"
    match = re.match(pattern, message.text.lower().strip())
    
    if not match:
        await message.reply(
            "❌ Неверный формат команды!\n"
            "Используйте: <code>Ранг X = Именительный Родительный Творительный</code>\n\n"
            "Пример: <code>Ранг 1 = Мишки мишек мишкой</code>",
            parse_mode="HTML"
        )
        return
    
    rank_level = int(match.group(1))
    nom = match.group(2).capitalize()
    gen = match.group(3).lower()
    ins = match.group(4).lower()
    
    if rank_level not in RANKS:
        await message.reply(f"❌ Неверный уровень ранга. Доступно от 1 до {max(RANKS.keys())}.")
        return
    
    await set_group_rank_names(message.chat.id, rank_level, nom, gen, ins)
    
    await message.reply(
        f"✅ Названия для <b>{rank_level} ранга</b> в этой группе обновлены:\n"
        f"👤 Кто? — <b>{nom}</b>\n"
        f"👥 Кого? — <b>{gen}</b>\n"
        f"🛠 Кем? — <b>{ins}</b>",
        parse_mode="HTML"
    )

@router.message(F.text.lower().in_({"кто админ?", "кто админ", "список админов", "список администраторов", "кто администрация"}))
async def handle_who_is_admin_command(message: types.Message):
    """Показывает список всех рангов и пользователей на них."""
    ranked_users = await get_all_ranked_users(message.chat.id)
    
    # Группируем пользователей по рангам из БД (только от 1 до 5)
    rank_groups = {level: [] for level in range(1, 6)}
    for u_id, level in ranked_users.items():
        if level in rank_groups:
            rank_groups[level].append(int(u_id))
            
    # Пытаемся найти реального создателя группы через Telegram API
    real_creator_id = None
    try:
        # Получаем список администраторов, чтобы найти владельца (creator)
        admins = await message.chat.get_administrators()
        for admin in admins:
            if admin.status == "creator":
                real_creator_id = admin.user.id
                # Если его нет в нашей группе 5 ранга (из БД), добавляем его виртуально для списка
                if real_creator_id not in rank_groups[5]:
                    rank_groups[5].append(real_creator_id)
                break
    except Exception as e:
        print(f"Ошибка при получении создателя чата: {e}")

    # Специально проверяем 1 ранг. Если в БД никого нет с 1 рангом, 
    # но пользователь жалуется, что его не видно, возможно он просто не в базе.
    # Мы показываем только тех, кто явно назначен или есть в БД.

    # Формируем список рангов для вывода
    rank_sections = []
    
    # Выводим от высшего к низшему (5 до 1)
    for level in range(5, 0, -1):
        users = rank_groups[level]
        # Для 1 ранга мы показываем секцию, только если там есть люди, 
        # чтобы не забивать список всеми участниками чата
        if not users:
            continue
            
        rank_name = await get_group_rank_name(message.chat.id, level, "nom")
        section = f"[{level}] <b>{rank_name}</b>\n"
        
        # Убираем дубликаты и пустые значения
        unique_users = list(set(users))
        for u_id in unique_users:
            mention = await get_mention_by_id(u_id)
            section += f" — {mention}\n"
        rank_sections.append(section)
    
    if not rank_sections:
        await message.reply("📜 На данный момент нет пользователей с назначенными рангами.")
        return

    response = "🎭 <b>Список администрации и рангов:</b>\n\n" + "\n".join(rank_sections)
    await message.reply(response, parse_mode="HTML")
