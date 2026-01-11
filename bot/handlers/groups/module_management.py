from aiogram import Router, types, F
from bot.utils.db_manager import get_disabled_modules, toggle_module
from bot.utils.filters import RankFilter
import re

router = Router()

# Доступные модули для управления
AVAILABLE_MODULES = {
    1: {"name": "Дуэли", "id": "duels"},
    2: {"name": "Русская рулетка", "id": "roulette"}
}

@router.message(F.text.lower() == ".кд лист", RankFilter(min_rank=3))
async def handle_module_list(message: types.Message):
    """
    Выводит список модулей и их статус.
    """
    disabled = await get_disabled_modules(message.chat.id)
    
    text = "<b>🛠 Управление модулями группы</b>\n\n"
    
    for idx, mod in AVAILABLE_MODULES.items():
        status = "❌ Выкл" if mod["id"] in disabled else "✅ Вкл"
        text += f"{status} — {mod['name']} [{idx}]\n"
    
    text += (
        "\nДля изменения статуса используйте:\n"
        "<code>.кд + [номер]</code> — Включить\n"
        "<code>.кд - [номер]</code> — Выключить\n\n"
        "<i>Например: .кд - 1</i>"
    )
    
    await message.reply(text, parse_mode="HTML")

@router.message(F.text.lower().startswith((".кд +", ".кд -")), RankFilter(min_rank=3))
async def handle_module_toggle(message: types.Message):
    """
    Включает или выключает модуль по его номеру.
    """
    text = message.text.lower()
    enable = "+" in text
    
    # Ищем номер модуля
    match = re.search(r'(\d+)', text)
    if not match:
        await message.reply("❌ Укажите номер модуля из списка <code>.кд лист</code>", parse_mode="HTML")
        return
    
    idx = int(match.group(1))
    if idx not in AVAILABLE_MODULES:
        await message.reply("❌ Модуль с таким номером не найден.")
        return
    
    module = AVAILABLE_MODULES[idx]
    await toggle_module(message.chat.id, module["id"], enable)
    
    status_text = "включен ✅" if enable else "выключен ❌"
    await message.reply(f"✅ Модуль <b>{module['name']}</b> успешно {status_text}!")
