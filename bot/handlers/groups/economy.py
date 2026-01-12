from aiogram import Router, types, F
from bot.utils.db_manager import get_user_balance, transfer_coins, update_user_balance
from bot.utils.filters import ModuleEnabledFilter
import logging

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("economy"))

@router.message(F.text.lower().in_({"баланс", "кошелек", "счет"}))
async def handle_balance(message: types.Message):
    """Показывает баланс пользователя."""
    balance = await get_user_balance(message.from_user.id)
    await message.reply(f"💰 Ваш текущий баланс: <code>{balance}</code> койнов.", parse_mode="HTML")

@router.message(F.text.lower().startswith("передать"))
async def handle_transfer(message: types.Message):
    """Передача койнов другому пользователю."""
    # 1. Проверяем наличие реплея
    if not message.reply_to_message:
        await message.reply("❌ Вы должны ответить на сообщение того, кому хотите передать койны.")
        return

    target_user = message.reply_to_message.from_user
    if target_user.id == message.from_user.id:
        await message.reply("❌ Нельзя передавать койны самому себе.")
        return

    if target_user.is_bot:
        return

    # 2. Парсим сумму
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("❌ Укажите сумму для передачи.\nПример: <code>передать 100</code> (в ответ на сообщение)", parse_mode="HTML")
        return

    amount = int(parts[1])
    if amount <= 0:
        await message.reply("❌ Сумма должна быть больше 0.")
        return

    # 3. Выполняем перевод
    success = await transfer_coins(message.from_user.id, target_user.id, amount)
    
    if success:
        await message.answer(
            f"✅ Вы успешно передали <b>{amount}</b> койнов пользователю {target_user.full_name}.",
            parse_mode="HTML"
        )
    else:
        await message.reply("❌ У вас недостаточно койнов для перевода.")

@router.message(F.text.lower().startswith("выдать"), F.from_user.id == 510134446) # ID создателя для теста
async def handle_give_coins(message: types.Message):
    """Админская команда для выдачи койнов (только для создателя)."""
    if not message.reply_to_message:
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].replace('-', '').isdigit():
        return

    amount = int(parts[1])
    target_user = message.reply_to_message.from_user
    
    new_balance = await update_user_balance(target_user.id, amount)
    await message.answer(f"💳 Баланс {target_user.full_name} обновлен. Текущий счет: <code>{new_balance}</code>", parse_mode="HTML")
