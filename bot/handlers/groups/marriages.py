import asyncio
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.utils.db_manager import (
    get_mention_by_id, 
    create_marriage, 
    get_marriage, 
    remove_marriage
)
from bot.handlers.groups.moderation import get_target_id

router = Router()

# Callback data для браков
class MarriageAction(CallbackData, prefix="marriage"):
    action: str  # accept, decline
    proposer_id: int
    target_id: int

def get_marriage_keyboard(proposer_id, target_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Согласен(а)", callback_data=MarriageAction(action="accept", proposer_id=proposer_id, target_id=target_id))
    builder.button(text="❌ Отказаться", callback_data=MarriageAction(action="decline", proposer_id=proposer_id, target_id=target_id))
    builder.adjust(2)
    return builder.as_markup()

def get_marriage_status(days):
    if days < 1: return "Молодожёны 💍"
    if days < 7: return "Медовый месяц 🍯"
    if days < 30: return "Крепкая пара 🤝"
    if days < 90: return "Любовный союз ❤️"
    if days < 180: return "Неразлучники ✨"
    if days < 365: return "Золотой стандарт 🌟"
    return "Вечная любовь ∞"

@router.message(F.text.lower().startswith("брак"))
async def marriage_invite(message: types.Message):
    target_user_id, _ = await get_target_id(message, "брак")
    
    if not target_user_id:
        await message.reply("❌ Укажите, с кем вы хотите вступить в брак (тег или ответ на сообщение).")
        return
        
    if target_user_id == message.from_user.id:
        await message.reply("🤡 Вы не можете жениться на самом себе.")
        return

    bot_info = await message.bot.get_me()
    if target_user_id == bot_info.id:
        await message.reply("🤖 Мое сердце принадлежит коду. Я не могу выйти за вас.")
        return

    # Проверка, не в браке ли уже кто-то
    if await get_marriage(message.from_user.id):
        await message.reply("❌ Вы уже состоите в браке! Сначала разведитесь.")
        return
    
    if await get_marriage(target_user_id):
        await message.reply("❌ Этот пользователь уже состоит в браке.")
        return

    proposer_mention = await get_mention_by_id(message.from_user.id)
    target_mention = await get_mention_by_id(target_user_id)
    
    await message.answer(
        f"💖 {proposer_mention} делает предложение руки и сердца {target_mention}!\n\n"
        f"{target_mention}, вы согласны вступить в брак?",
        reply_markup=get_marriage_keyboard(message.from_user.id, target_user_id),
        parse_mode="HTML"
    )

@router.callback_query(MarriageAction.filter(F.action == "accept"))
async def accept_marriage(callback: types.CallbackQuery, callback_data: MarriageAction):
    if callback.from_user.id != callback_data.target_id:
        await callback.answer("❌ Это предложение не вам!", show_alert=True)
        return

    proposer_id = callback_data.proposer_id
    target_id = callback_data.target_id
    
    # Еще раз проверяем, не успел ли кто-то вступить в брак
    if await get_marriage(proposer_id) or await get_marriage(target_id):
        await callback.answer("❌ Кто-то из вас уже успел вступить в брак!", show_alert=True)
        await callback.message.delete()
        return

    await create_marriage(proposer_id, target_id)
    
    proposer_mention = await get_mention_by_id(proposer_id)
    target_mention = await get_mention_by_id(target_id)
    
    await callback.message.edit_text(
        f"🎉 Поздравляем! {proposer_mention} и {target_mention} теперь официально в браке! 🥳💍\n\n"
        f"Желаем вам долгой и счастливой совместной жизни!",
        parse_mode="HTML"
    )

@router.callback_query(MarriageAction.filter(F.action == "decline"))
async def decline_marriage(callback: types.CallbackQuery, callback_data: MarriageAction):
    if callback.from_user.id != callback_data.target_id:
        await callback.answer("❌ Это предложение не вам!", show_alert=True)
        return

    target_mention = await get_mention_by_id(callback_data.target_id)
    await callback.message.edit_text(
        f"💔 {target_mention} отклонил(а) предложение руки и сердца... Сердце разбито.",
        parse_mode="HTML"
    )

@router.message(F.text.lower() == "мой брак")
async def my_marriage(message: types.Message):
    marriage = await get_marriage(message.from_user.id)
    
    if not marriage:
        await message.reply("👀 Вы пока не состоите в браке. Используйте 'Брак [пользователь]', чтобы сделать предложение.")
        return
        
    partner_id = [p for p in marriage["partners"] if p != message.from_user.id][0]
    partner_mention = await get_mention_by_id(partner_id)
    
    created_at = datetime.fromisoformat(marriage["created_at"])
    duration = datetime.now() - created_at
    days = duration.days
    
    status = get_marriage_status(days)
    
    await message.reply(
        f"💒 <b>Ваш брак</b>\n\n"
        f"👤 <b>Партнер:</b> {partner_mention}\n"
        f"📅 <b>Вместе уже:</b> {days} дн.\n"
        f"📜 <b>Статус:</b> {status}\n"
        f"⏰ <b>Дата свадьбы:</b> {created_at.strftime('%d.%m.%Y')}",
        parse_mode="HTML"
    )

@router.message(F.text.lower() == "развод")
async def divorce(message: types.Message):
    marriage = await get_marriage(message.from_user.id)
    
    if not marriage:
        await message.reply("🤔 Вы и так не в браке.")
        return
        
    partner_id = [p for p in marriage["partners"] if p != message.from_user.id][0]
    partner_mention = await get_mention_by_id(partner_id)
    
    await remove_marriage(message.from_user.id)
    
    await message.reply(
        f"🥀 Брак между вами и {partner_mention} был расторгнут.\n"
        f"Теперь вы снова свободны.",
        parse_mode="HTML"
    )
