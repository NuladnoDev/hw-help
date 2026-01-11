from aiogram import Router, types, F
from bot.utils.db_manager import get_permission_settings, set_permission_rank, RANKS
from bot.utils.filters import RankFilter
import re
import logging

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

@router.message(
    F.text.lower().startswith(".права лист")
    | F.text.lower().startswith("/права лист")
    | F.text.lower().startswith("!права лист"),
    RankFilter(min_rank=5),
)
async def handle_permissions_list(message: types.Message):
    logging.info(f"DEBUG: Получена команда .права лист от {message.from_user.id}")
    try:
        settings = await get_permission_settings(message.chat.id)
        text = "<b>🔐 Управление правами группы</b>\n\n"
        for idx, action in MODERATION_ACTIONS.items():
            current_rank = settings.get(action["id"], action["default"])
            rank_name = RANKS.get(current_rank, "Неизвестно")
            text += f"[{idx}] {action['name']}: <b>{rank_name}</b> ({current_rank})\n"
        
        text += "\nДля изменения прав используйте:\n<code>.права [номер] = [ранг]</code>\n\n<i>Например: .права 1 = 3 (разрешит баны с 3 ранга)</i>"
        
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка в handle_permissions_list: {e}")
        await message.answer("❌ Произошла ошибка при выводе списка прав.")

@router.message(
    F.text.lower().startswith(".права")
    | F.text.lower().startswith("/права")
    | F.text.lower().startswith("!права"),
    RankFilter(min_rank=5),
)
async def handle_permission_change(message: types.Message):
    logging.info(f"DEBUG: Получена команда .права от {message.from_user.id}")
    try:
        text = message.text.lower()
        if "лист" in text:
            return
        
        match = re.search(r'права\s+(\d+)\s*=\s*(\d+)', text)
        if not match:
            return
            
        action_idx = int(match.group(1))
        new_rank = int(match.group(2))
        
        if action_idx not in MODERATION_ACTIONS:
            await message.answer("❌ Действие с таким номером не найдено.")
            return
            
        if new_rank not in RANKS:
            await message.answer(f"❌ Неверный ранг. Доступно от 0 до 5.")
            return
            
        action = MODERATION_ACTIONS[action_idx]
        await set_permission_rank(message.chat.id, action["id"], new_rank)
        
        await message.answer(
            f"✅ Права изменены!\n"
            f"Действие: <b>{action['name']}</b>\n"
            f"Минимальный ранг теперь: <b>{RANKS[new_rank]}</b> ({new_rank})",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка в handle_permission_change: {e}")
        await message.answer("❌ Произошла ошибка при изменении прав.")
