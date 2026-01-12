from aiogram import Router, types, F
from bot.utils.db_manager import (
    create_club, get_club_by_name, delete_club, join_club, 
    leave_club, get_user_clubs, get_mention_by_id, get_all_clubs
)
from bot.utils.filters import RankFilter, ModuleEnabledFilter
import re

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("clubs"))

@router.message(F.text.lower().startswith("+кружок"))
async def handle_create_club(message: types.Message):
    """Создает новый кружок. Формат: +кружок Название"""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Укажите название кружка: <code>+кружок Название</code>", parse_mode="HTML")
        return
    
    club_name = parts[1].strip()
    if len(club_name) > 32:
        await message.reply("❌ Название кружка слишком длинное (макс. 32 символа).")
        return

    # Проверяем, нет ли кружка с таким названием в этом чате
    existing_club = await get_club_by_name(message.chat.id, club_name)
    if existing_club:
        await message.reply(f"❌ Кружок с названием <b>{club_name}</b> уже существует.")
        return

    club_id = await create_club(message.chat.id, club_name, message.from_user.id)
    if club_id:
        await message.reply(f"✅ Кружок <b>{club_name}</b> успешно создан! Вы стали его создателем.", parse_mode="HTML")
    else:
        await message.reply("❌ Произошла ошибка при создании кружка.")

@router.message(F.text.lower().startswith("-кружок"))
async def handle_delete_or_leave_club(message: types.Message):
    """Удаляет кружок (если создатель) или выходит из него. Формат: -кружок Название"""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Укажите название кружка: <code>-кружок Название</code>", parse_mode="HTML")
        return
        
    club_name = parts[1].strip()
    club = await get_club_by_name(message.chat.id, club_name)
    
    if not club:
        await message.reply(f"❌ Кружок <b>{club_name}</b> не найден.")
        return

    user_clubs = await get_user_clubs(message.chat.id, message.from_user.id)
    is_member = any(c["id"] == club["id"] for c in user_clubs)
    
    if not is_member:
        await message.reply(f"❌ Вы не состоите в кружке <b>{club_name}</b>.")
        return

    if club["creator_id"] == message.from_user.id:
        # Если создатель - удаляем весь кружок
        await delete_club(club["id"])
        await message.reply(f"💥 Кружок <b>{club['name']}</b> был удален создателем.")
    else:
        # Если не создатель - просто выходим
        await leave_club(message.chat.id, club["id"], message.from_user.id)
        await message.reply(f"🚪 Вы покинули кружок <b>{club['name']}</b>.")

@router.message(F.text.lower().startswith("кружок "))
async def handle_join_club(message: types.Message):
    """Вступает в кружок. Формат: кружок Название"""
    parts = message.text.split(maxsplit=1)
    club_name = parts[1].strip()
    
    club = await get_club_by_name(message.chat.id, club_name)
    if not club:
        await message.reply(f"❌ Кружок <b>{club_name}</b> не найден.")
        return

    user_clubs = await get_user_clubs(message.chat.id, message.from_user.id)
    if any(c["id"] == club["id"] for c in user_clubs):
        await message.reply(f"ℹ️ Вы уже состоите в кружке <b>{club['name']}</b>.")
        return

    if await join_club(message.chat.id, club["id"], message.from_user.id):
        await message.reply(f"🤝 Вы вступили в кружок <b>{club['name']}</b>!")
    else:
        await message.reply("❌ Не удалось вступить в кружок.")

@router.message(F.text.lower() == "кружок")
async def handle_my_clubs(message: types.Message):
    """Показывает кружки пользователя."""
    user_clubs = await get_user_clubs(message.chat.id, message.from_user.id)
    
    if user_clubs:
        clubs_str = ", ".join([f"<b>{c['name']}</b>" for c in user_clubs])
        text = f"🎨 Вы состоите в кружках: {clubs_str}\n\n"
        text += "💡 Чтобы выйти, используйте: <code>-кружок Название</code>"
    else:
        text = "❌ Вы пока не состоите ни в одном кружке.\n\n"
        text += "💡 Чтобы создать свой: <code>+кружок Название</code>\n"
        text += "💡 Чтобы вступить в существующий: <code>кружок Название</code>"
    
    await message.reply(text, parse_mode="HTML")

@router.message(F.text.lower() == "кружки")
async def handle_clubs_list(message: types.Message):
    """Показывает список всех кружков чата."""
    clubs = await get_all_clubs(message.chat.id)
    
    if not clubs:
        text = "🏘 В этом чате пока нет ни одного кружка.\n\n"
    else:
        text = "<b>🎭 Кружки этого чата:</b>\n\n"
        for i, club in enumerate(clubs, 1):
            text += f"{i}. <b>{club['name']}</b>\n"
        text += "\n"
        
    text += "💡 Создать свой: <code>+кружок Название</code>\n"
    text += "💡 Вступить: <code>кружок Название</code>"
    
    await message.reply(text, parse_mode="HTML")
