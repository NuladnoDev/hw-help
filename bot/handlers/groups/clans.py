from aiogram import Router, types, F
from bot.utils.db_manager import (
    create_clan,
    get_clan_by_name,
    delete_clan,
    join_clan,
    leave_clan,
    get_user_clan,
    get_mention_by_id,
    get_all_clans,
    apply_once_level_bonus
)
from bot.utils.filters import RankFilter, ModuleEnabledFilter
import re

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("clans"))

@router.message(F.text.lower().startswith("+клан"))
async def handle_create_clan(message: types.Message):
    """Создает новый клан. Формат: +клан Название"""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Укажите название клана: <code>+клан Название</code>", parse_mode="HTML")
        return
    
    clan_name = parts[1].strip()
    if len(clan_name) > 32:
        await message.reply("❌ Название клана слишком длинное (макс. 32 символа).")
        return

    # Проверяем, не состоит ли уже в клане
    existing_user_clan = await get_user_clan(message.chat.id, message.from_user.id)
    if existing_user_clan:
        await message.reply(f"❌ Вы уже состоите в клане <b>{existing_user_clan['name']}</b>. Сначала выйдите из него.")
        return

    # Проверяем, нет ли клана с таким названием в этом чате
    existing_clan = await get_clan_by_name(message.chat.id, clan_name)
    if existing_clan:
        await message.reply(f"❌ Клан с названием <b>{clan_name}</b> уже существует в этом чате.")
        return

    clan_id = await create_clan(message.chat.id, clan_name, message.from_user.id)
    if clan_id:
        await message.reply(f"✅ Клан <b>{clan_name}</b> успешно создан! Вы стали его создателем.", parse_mode="HTML")
        await apply_once_level_bonus(message.from_user.id, "clan", 200)
    else:
        await message.reply("❌ Произошла ошибка при создании клана.")

@router.message(F.text.lower().startswith("-клан"))
async def handle_delete_or_leave_clan(message: types.Message):
    """Удаляет клан (если создатель) или выходит из него. Формат: -клан"""
    user_clan = await get_user_clan(message.chat.id, message.from_user.id)
    if not user_clan:
        await message.reply("❌ Вы не состоите ни в одном клане.")
        return

    if user_clan["creator_id"] == message.from_user.id:
        # Если создатель - удаляем весь клан
        await delete_clan(user_clan["id"])
        await message.reply(f"💥 Клан <b>{user_clan['name']}</b> был расформирован создателем.")
    else:
        # Если не создатель - просто выходим
        await leave_clan(message.chat.id, message.from_user.id)
        await message.reply(f"🚪 Вы покинули клан <b>{user_clan['name']}</b>.")

@router.message(F.text.lower().startswith("клан "))
async def handle_join_clan(message: types.Message):
    """Вступает в клан. Формат: клан Название"""
    parts = message.text.split(maxsplit=1)
    clan_name = parts[1].strip()
    
    clan = await get_clan_by_name(message.chat.id, clan_name)
    if not clan:
        await message.reply(f"❌ Клан <b>{clan_name}</b> не найден.")
        return

    existing_user_clan = await get_user_clan(message.chat.id, message.from_user.id)
    if existing_user_clan:
        if existing_user_clan["id"] == clan["id"]:
            await message.reply(f"ℹ️ Вы уже состоите в клане <b>{clan['name']}</b>.")
        else:
            await message.reply(f"❌ Вы уже состоите в клане <b>{existing_user_clan['name']}</b>. Сначала выйдите из него.")
        return

    if await join_clan(message.chat.id, clan["id"], message.from_user.id):
        await message.reply(f"🤝 Вы успешно вступили в клан <b>{clan['name']}</b>!")
    else:
        await message.reply("❌ Не удалось вступить в клан.")

@router.message(F.text.lower() == "клан")
async def handle_my_clan(message: types.Message):
    """Показывает клан пользователя."""
    user_clan = await get_user_clan(message.chat.id, message.from_user.id)
    
    if user_clan:
        text = f"🛡 Вы состоите в клане <b>{user_clan['name']}</b>\n\n"
        text += "💡 Чтобы выйти из него, используйте команду: <code>-клан</code>"
    else:
        text = "❌ Вы пока не состоите в клане.\n\n"
        text += "💡 Чтобы создать свой, используйте: <code>+клан Название</code>\n"
        text += "💡 Чтобы вступить в существующий: <code>клан Название</code>"
    
    await message.reply(text, parse_mode="HTML")

@router.message(F.text.lower() == "кланы")
async def handle_clans_list(message: types.Message):
    """Показывает список всех кланов чата."""
    clans = await get_all_clans(message.chat.id)
    
    if not clans:
        text = "🏘 В этом чате пока нет ни одного клана.\n\n"
    else:
        text = "<b>🏰 Кланы этого чата:</b>\n\n"
        for i, clan in enumerate(clans, 1):
            text += f"{i}. <b>{clan['name']}</b>\n"
        text += "\n"
        
    text += "💡 Создать свой: <code>+клан Название</code>\n"
    text += "💡 Вступить: <code>клан Название</code>"
    
    await message.reply(text, parse_mode="HTML")
