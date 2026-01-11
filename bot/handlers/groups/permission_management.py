from aiogram import Router, types, F
from bot.utils.db_manager import get_permission_settings, set_permission_rank, RANKS
from bot.utils.filters import RankFilter
import re

router = Router()

# Действия, права на которые можно настраивать
# По умолчанию берем значения, которые обычно используются в фильтрах
MODERATION_ACTIONS = {
    1: {"name": "Бан пользователей", "id": "ban", "default": 4},
    2: {"name": "Мут пользователей", "id": "mute", "default": 2},
    3: {"name": "Варны (выдача/снятие)", "id": "warn", "default": 2},
    4: {"name": "Удаление сообщений", "id": "delete", "default": 2},
    5: {"name": "Назначение рангов", "id": "set_rank", "default": 5},
    6: {"name": "Выдача наград", "id": "award", "default": 3},
}

@router.message(F.text.lower().contains(".права лист"), RankFilter(min_rank=5))
async def handle_permissions_list(message: types.Message):
    """
    Выводит список действий и минимальный ранг для них.
    """
    settings = await get_permission_settings(message.chat.id)
    
    text = "<b>🔐 Управление правами группы</b>\n\n"
    
    for idx, action in MODERATION_ACTIONS.items():
        current_rank = settings.get(action["id"], action["default"])
        rank_name = RANKS.get(current_rank, "Неизвестно")
        text += f"[{idx}] {action['name']}: <b>{rank_name}</b> ({current_rank})\n"
    
    text += (
        "\nДля изменения прав используйте:\n"
        "<code>.права [номер] = [ранг]</code>\n\n"
        "<i>Например: .права 1 = 3 (разрешит баны с 3 ранга)</i>"
    )
    
    await message.reply(text, parse_mode="HTML")

@router.message(F.text.lower().contains(".права") & F.text.contains("="), RankFilter(min_rank=5))
async def handle_permission_change(message: types.Message):
    """
    Изменяет минимальный ранг для действия.
    Формат: .права 1 = 3
    """
    text = message.text.lower()
    
    # Ищем номер действия и новый ранг
    match = re.search(r'\.права\s+(\d+)\s*=\s*(\d+)', text)
    if not match:
        # Если это просто .права без параметров, не спамим (может быть ошибка ввода)
        if text.strip() == ".права":
            return
        await message.reply("❌ Неверный формат. Используйте: <code>.права [номер] = [ранг]</code>", parse_mode="HTML")
        return
    
    action_idx = int(match.group(1))
    new_rank = int(match.group(2))
    
    if action_idx not in MODERATION_ACTIONS:
        await message.reply("❌ Действие с таким номером не найдено.")
        return
        
    if new_rank not in RANKS:
        await message.reply(f"❌ Неверный ранг. Доступно от 0 до 5.")
        return
    
    action = MODERATION_ACTIONS[action_idx]
    await set_permission_rank(message.chat.id, action["id"], new_rank)
    
    await message.reply(
        f"✅ Права изменены!\n"
        f"Действие: <b>{action['name']}</b>\n"
        f"Минимальный ранг теперь: <b>{RANKS[new_rank]}</b> ({new_rank})"
    )
