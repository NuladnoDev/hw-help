from aiogram import Router, types, F
from bot.utils.db_manager import get_disabled_modules, toggle_module
from bot.utils.filters import RankFilter
import re
import logging

router = Router()

# Доступные модули для управления
AVAILABLE_MODULES = {
    1: {"name": "Дуэли", "id": "duels"},
    2: {"name": "Русская рулетка", "id": "roulette"},
    3: {"name": "Кланы", "id": "clans"},
    4: {"name": "Кружки", "id": "clubs"},
    5: {"name": "Анекдоты", "id": "jokes"},
    6: {"name": "Погода", "id": "weather"},
    7: {"name": "Репутация", "id": "reputation"},
    8: {"name": "HW-Антиспам", "id": "antispam"},
    9: {"name": "Экономика", "id": "economy"},
    10: {"name": "Шипперинг", "id": "shippering"},
    11: {"name": "Повтори", "id": "repeat"},
    12: {"name": "Инфа", "id": "info"},
    13: {"name": "Данет", "id": "yesno"},
    14: {"name": "Кто", "id": "who"},
    15: {"name": "Выбери", "id": "choose"},
    16: {"name": "Пинг", "id": "ping"},
    17: {"name": "Каталог", "id": "catalog"}
}

@router.message(
    F.text.lower().startswith(".кд лист")
    | F.text.lower().startswith("/кд лист")
    | F.text.lower().startswith("!кд лист"),
    RankFilter(min_rank=3),
)
async def handle_module_list(message: types.Message):
    logging.info(f"DEBUG: Получена команда .кд лист от {message.from_user.id}")
    try:
        disabled = await get_disabled_modules(message.chat.id)
        text = "<b>🛠 Управление модулями группы</b>\n\n"
        for idx, mod in AVAILABLE_MODULES.items():
            status = "❌ Выкл" if mod["id"] in disabled else "✅ Вкл"
            text += f"{status} — {mod['name']} [{idx}]\n"
        text += "\nДля изменения статуса используйте:\n<code>.кд + [номер]</code> — Включить\n<code>.кд - [номер]</code> — Выключить\n\n<i>Например: .кд - 1</i>"
        
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка в handle_module_list: {e}")
        await message.answer("❌ Произошла ошибка при выводе списка модулей.")

@router.message(
    F.text.lower().startswith(".кд")
    | F.text.lower().startswith("/кд")
    | F.text.lower().startswith("!кд"),
    RankFilter(min_rank=3),
)
async def handle_module_toggle(message: types.Message):
    logging.info(f"DEBUG: Получена команда .кд +/- от {message.from_user.id}")
    try:
        text = message.text.lower()
        if "лист" in text:
            return
        enable = "+" in text
        match = re.search(r'(\d+)', text)
        if not match:
            await message.answer("❌ Укажите номер модуля из списка <code>.кд лист</code>", parse_mode="HTML")
            return
        idx = int(match.group(1))
        if idx not in AVAILABLE_MODULES:
            await message.answer("❌ Модуль с таким номером не найден.")
            return
        module = AVAILABLE_MODULES[idx]
        await toggle_module(message.chat.id, module["id"], enable)
        status_text = "включен ✅" if enable else "выключен ❌"
        await message.answer(f"✅ Модуль <b>{module['name']}</b> успешно {status_text}!", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка в handle_module_toggle: {e}")
        await message.answer("❌ Произошла ошибка при изменении модуля.")
