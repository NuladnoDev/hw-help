import random
import asyncio
from aiogram import Router, types, F
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.utils.db_manager import get_mention_by_id, update_user_cache
from bot.handlers.groups.moderation import get_target_id

router = Router()

# Callback data для дуэлей
class DuelAction(CallbackData, prefix="duel"):
    action: str  # invite, accept, decline, shoot, air
    challenger_id: int
    target_id: int
    current_turn: int = 0

# Хранилище активных дуэлей и приглашений
active_duels = {}
pending_invitations = {} # {message_id: bool}

def get_duel_keyboard(challenger_id, target_id, is_invitation=True, current_turn=None):
    builder = InlineKeyboardBuilder()
    if is_invitation:
        builder.button(text="✅ Принять", callback_data=DuelAction(action="accept", challenger_id=challenger_id, target_id=target_id))
        builder.button(text="❌ Отказаться", callback_data=DuelAction(action="decline", challenger_id=challenger_id, target_id=target_id))
    else:
        builder.button(text="🔫 Стрельнуть", callback_data=DuelAction(action="shoot", challenger_id=challenger_id, target_id=target_id, current_turn=current_turn))
        builder.button(text="☁️ В воздух", callback_data=DuelAction(action="air", challenger_id=challenger_id, target_id=target_id, current_turn=current_turn))
    builder.adjust(2)
    return builder.as_markup()

@router.message(F.text.lower().startswith("дуэль"))
async def handle_duel_command(message: types.Message):
    """Приглашение на дуэль."""
    target_user_id, _ = await get_target_id(message, "дуэль")
    
    if not target_user_id:
        await message.reply("❌ Укажите, кого вы вызываете на дуэль (тег или ответ на сообщение).")
        return
        
    if target_user_id == message.from_user.id:
        await message.reply("🤡 Вы не можете вызвать на дуэль самого себя.")
        return

    bot_info = await message.bot.get_me()
    if target_user_id == bot_info.id:
        await message.reply("🤖 Я не участвую в дуэлях, у меня встроенный аимбот.")
        return

    challenger_mention = await get_mention_by_id(message.from_user.id)
    target_mention = await get_mention_by_id(target_user_id)
    
    sent_message = await message.answer(
        f"⚔️ {challenger_mention} вызывает на дуэль {target_mention}!\n\n"
        f"{target_mention}, вы принимаете вызов?\n"
        f"<i>⏳ Предложение автоматически отклонится через 2 минуты.</i>",
        reply_markup=get_duel_keyboard(message.from_user.id, target_user_id),
        parse_mode="HTML"
    )

    # Логика авто-отмены через 2 минуты
    msg_id = sent_message.message_id
    pending_invitations[msg_id] = True
    
    async def auto_cancel_duel(chat_id, message_id, target_mention):
        await asyncio.sleep(120)
        if pending_invitations.get(message_id):
            try:
                await message.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
                await message.bot.send_message(
                    chat_id, 
                    f"⏰ Время вызова истекло. {target_mention} так и не решился принять дуэль.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            finally:
                pending_invitations.pop(message_id, None)

    asyncio.create_task(auto_cancel_duel(message.chat.id, msg_id, target_mention))

@router.callback_query(DuelAction.filter(F.action == "accept"))
async def accept_duel(callback: types.CallbackQuery, callback_data: DuelAction):
    if callback.from_user.id != callback_data.target_id:
        await callback.answer("❌ Это не ваш вызов!", show_alert=True)
        return

    challenger_id = callback_data.challenger_id
    target_id = callback_data.target_id
    
    # Определяем, кто ходит первым
    first_turn = random.choice([challenger_id, target_id])
    
    challenger_mention = await get_mention_by_id(challenger_id)
    target_mention = await get_mention_by_id(target_id)
    first_mention = await get_mention_by_id(first_turn)
    
    # Убираем из ожидающих
    pending_invitations.pop(callback.message.message_id, None)
    
    await callback.message.edit_text(
        f"🔔 Дуэль между {challenger_mention} и {target_mention} началась!\n\n"
        f"🎲 Жребий пал на {first_mention}. Твой ход!",
        reply_markup=get_duel_keyboard(challenger_id, target_id, is_invitation=False, current_turn=first_turn),
        parse_mode="HTML"
    )

@router.callback_query(DuelAction.filter(F.action == "decline"))
async def decline_duel(callback: types.CallbackQuery, callback_data: DuelAction):
    if callback.from_user.id != callback_data.target_id:
        await callback.answer("❌ Это не ваш вызов!", show_alert=True)
        return

    target_mention = await get_mention_by_id(callback_data.target_id)
    # Убираем из ожидающих
    pending_invitations.pop(callback.message.message_id, None)
    
    # Убираем кнопки у старого сообщения
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
        
    await callback.message.answer(f"💨 {target_mention} испугался и отклонил вызов на дуэль.", parse_mode="HTML")

@router.callback_query(DuelAction.filter(F.action.in_({"shoot", "air"})))
async def handle_duel_turn(callback: types.CallbackQuery, callback_data: DuelAction):
    if callback.from_user.id != callback_data.current_turn:
        await callback.answer("⏳ Сейчас не ваш ход!", show_alert=True)
        return

    challenger_id = callback_data.challenger_id
    target_id = callback_data.target_id
    current_player_id = callback.from_user.id
    opponent_id = target_id if current_player_id == challenger_id else challenger_id
    
    current_mention = await get_mention_by_id(current_player_id)
    opponent_mention = await get_mention_by_id(opponent_id)
    
    if callback_data.action == "air":
        await callback.message.edit_text(
            f"☁️ {current_mention} выстрелил в воздух, проявив милосердие (или просто промахнулся по небу).\n\n"
            f"👉 Ход переходит к {opponent_mention}!",
            reply_markup=get_duel_keyboard(challenger_id, target_id, is_invitation=False, current_turn=opponent_id),
            parse_mode="HTML"
        )
        return

    # Логика выстрела (шанс попадания 40%)
    hit = random.random() < 0.4
    
    if hit:
        # Убираем кнопки у старого сообщения
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        victory_messages = [
            f"💥 БАХ! {current_mention} точным выстрелом сразил {opponent_mention} наповал!",
            f"🔫 {current_mention} спустил курок и отправил {opponent_mention} в глубокий нокаут!",
            f"⚡️ {current_mention} оказался быстрее и не оставил {opponent_mention} ни единого шанса!",
            f"🎯 {current_mention} продемонстрировал мастерство стрельбы и одержал победу над {opponent_mention}!",
            f"💀 {current_mention} хладнокровно нажал на спуск, завершив этот поединок победой!"
        ]
        win_text = random.choice(victory_messages)

        await callback.message.answer(
            f"{win_text}\n\n"
            f"🏆 Победитель дуэли: {current_mention}!",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"💨 {current_mention} нажал на курок, но пуля прошла в миллиметре от {opponent_mention}!\n\n"
            f"👉 Ход переходит к {opponent_mention}!",
            reply_markup=get_duel_keyboard(challenger_id, target_id, is_invitation=False, current_turn=opponent_id),
            parse_mode="HTML"
        )
