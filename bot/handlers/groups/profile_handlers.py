from aiogram import Router, types, F
from bot.modules.profile import get_user_profile, generate_level_card_image
from bot.handlers.groups.moderation import get_target_id
from bot.keyboards.profile_keyboards import ProfileAction, get_profile_kb, get_level_kb
from bot.utils.db_manager import (
    set_description, remove_description, get_description, 
    get_awards, get_mention_by_id, set_city, remove_city, get_city,
    set_quote, remove_quote, get_quote, get_user_level
)
import re
import logging

router = Router()

# Фильтр для проверки, что событие произошло в группе или супергруппе
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(F.text.lower().startswith("+описание"))
async def handle_set_description(message: types.Message):
    """
    Устанавливает описание профиля.
    """
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Вы не указали описание. Используйте: <code>+Описание (ваш текст)</code>", parse_mode="HTML")
        return
    
    new_desc = parts[1].strip()
    if len(new_desc) > 200:
        await message.reply("❌ Описание слишком длинное (максимум 200 символов).")
        return
    
    await set_description(message.from_user.id, new_desc)
    await message.reply("✅ Описание профиля обновлено!")

@router.message(F.text.lower().startswith("+город"))
async def handle_set_city(message: types.Message):
    """
    Устанавливает город в профиле.
    """
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Вы не указали город. Используйте: <code>+Город (название)</code>", parse_mode="HTML")
        return
    
    city_name = parts[1].strip().capitalize()
    if len(city_name) > 40:
        await message.reply("❌ Название города слишком длинное (максимум 40 символов).")
        return
    
    await set_city(message.from_user.id, city_name)
    await message.reply(f"✅ В профиль добавлен город: <b>{city_name}</b>", parse_mode="HTML")

@router.message(F.text.lower().startswith("+цитата"))
async def handle_set_quote(message: types.Message):
    """
    Устанавливает цитату в профиле.
    """
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Вы не указали цитату. Используйте: <code>+Цитата (ваш текст)</code>", parse_mode="HTML")
        return
    
    new_quote = parts[1].strip()
    if len(new_quote) > 300:
        await message.reply("❌ Цитата слишком длинная (максимум 300 символов).")
        return
    
    await set_quote(message.from_user.id, new_quote)
    await message.reply("✅ Цитата профиля обновлена!")

@router.message(F.text.lower().startswith("-город"))
async def handle_remove_city(message: types.Message):
    """
    Удаляет город из профиля.
    """
    if await remove_city(message.from_user.id):
        await message.reply("✅ Город удален из вашего профиля.")
    else:
        await message.reply("❌ В вашем профиле не был указан город.")

@router.message(F.text.lower().startswith("-цитата"))
async def handle_remove_quote(message: types.Message):
    """
    Удаляет цитату из профиля.
    """
    if await remove_quote(message.from_user.id):
        await message.reply("✅ Цитата профиля удалена.")
    else:
        await message.reply("❌ У вас не было установлено цитаты.")

@router.message(F.text.lower().startswith("-описание"))
async def handle_remove_description(message: types.Message):
    """
    Удаляет описание профиля.
    """
    if await remove_description(message.from_user.id):
        await message.reply("✅ Описание профиля удалено.")
    else:
        await message.reply("❌ У вас не было установлено описание.")

@router.callback_query(ProfileAction.filter())
async def handle_profile_callbacks(query: types.CallbackQuery, callback_data: ProfileAction):
    """
    Обработчик кнопок 'Описание' и 'Награды'.
    Отправляет информацию сообщением, а не алертом.
    """
    target_user_id = callback_data.user_id
    target_mention = await get_mention_by_id(target_user_id)
    
    if callback_data.action == "description":
        desc = await get_description(target_user_id)
        if desc:
            await query.message.answer(f"📝 Описание пользователя {target_mention}:\n{desc}", parse_mode="HTML")
        else:
            await query.message.answer(f"📝 У пользователя {target_mention} пока нет описания.", parse_mode="HTML")
        await query.answer()
            
    elif callback_data.action == "awards":
        awards = await get_awards(query.message.chat.id, target_user_id)
        if not awards:
            await query.message.answer(f"🏆 У пользователя {target_mention} пока нет наград.", parse_mode="HTML")
            await query.answer()
            return
            
        response = f"🏆 <b>Награды пользователя {target_mention}:</b>\n\n"
        for i, award in enumerate(awards, 1):
            from_mention = await get_mention_by_id(award["from_id"])
            response += f"награда [{i}] | {award['text']} (от {from_mention})\n"
        
        response += f"\nЧтобы убрать награду, используйте:\n<code>-награда (тег) (номер)</code>"
        
        await query.message.answer(response, parse_mode="HTML")
        await query.answer()

    elif callback_data.action == "quote":
        quote = await get_quote(target_user_id)
        if quote:
            await query.message.answer(f"💬 Цитата пользователя {target_mention}:\n\n<i>«{quote}»</i>", parse_mode="HTML")
        else:
            await query.message.answer(f"💬 У пользователя {target_mention} нет цитаты.", parse_mode="HTML")
        await query.answer()

    elif callback_data.action == "level":
        level_data = await get_user_level(target_user_id)
        level = level_data["level"]
        xp = level_data["xp"]
        needed = level_data["needed_xp"]
        remaining = level_data["remaining_xp"]
        next_reward = level_data["next_reward_coins"]
        
        # Получаем имя пользователя для карточки
        try:
            member = await query.message.chat.get_member(target_user_id)
            username = member.user.full_name
        except:
            username = "Пользователь"
            
        card_buf = await generate_level_card_image(target_user_id, username)
        
        text = (
            f"⭐ <b>Уровень пользователя {target_mention}</b>\n\n"
            f"Текущий уровень: <b>{level}</b>\n"
            f"Опыт: <b>{xp}</b> / <b>{needed}</b>\n\n"
            f"До следующего уровня осталось: <b>{remaining}</b> XP\n"
            f"Награда за следующий уровень: <b>{next_reward}</b> койнов\n\n"
            f"💡 <a href='https://telegra.ph/Pomoshch-po-komandam-01-11#Уровень-пользователя'>Как получить опыт?</a>"
        )
        
        if card_buf:
            photo = types.BufferedInputFile(card_buf.getvalue(), filename=f"level_{target_user_id}.png")
            if query.message.photo:
                await query.message.edit_media(
                    media=types.InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"),
                    reply_markup=get_level_kb(target_user_id)
                )
            else:
                await query.message.answer_photo(
                    photo=photo,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=get_level_kb(target_user_id)
                )
        else:
            # Фолбэк на текст, если картинка не сгенерилась
            if query.message.photo:
                await query.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=get_level_kb(target_user_id))
            else:
                await query.message.edit_text(text, parse_mode="HTML", reply_markup=get_level_kb(target_user_id))
        await query.answer()

    elif callback_data.action == "back":
        # Возвращаемся к обычному тексту профиля с графиком активности
        from bot.modules.profile import build_profile_text, generate_activity_chart
        profile_text, has_quote = await build_profile_text(query.message, target_user_id)
        chart_buf = await generate_activity_chart(target_user_id)
        
        if query.message.photo and chart_buf:
            photo = types.BufferedInputFile(chart_buf.getvalue(), filename=f"chart_{target_user_id}.png")
            await query.message.edit_media(
                media=types.InputMediaPhoto(media=photo, caption=profile_text, parse_mode="HTML"),
                reply_markup=get_profile_kb(target_user_id, has_quote=has_quote)
            )
        elif query.message.photo:
            await query.message.edit_caption(
                caption=profile_text,
                parse_mode="HTML",
                reply_markup=get_profile_kb(target_user_id, has_quote=has_quote)
            )
        else:
            await query.message.edit_text(
                profile_text,
                parse_mode="HTML",
                reply_markup=get_profile_kb(target_user_id, has_quote=has_quote)
            )
        await query.answer()

@router.message(F.text.lower().regexp(r'^(кто ты|ты кто|профиль|кто такой|кто я)'))
async def handle_profile_command(message: types.Message):
    """
    Обработчик команд профиля (кто ты, ты кто, профиль, кто такой, кто я).
    """
    text = message.text.lower()
    
    # Если команда 'кто я', показываем профиль отправителя
    if text == "кто я":
        await get_user_profile(message, message.from_user.id)
        return

    # Определяем имя команды для корректного парсинга аргументов в get_target_id
    command_name = ""
    if text.startswith("кто ты"): command_name = "кто ты"
    elif text.startswith("ты кто"): command_name = "ты кто"
    elif text.startswith("кто такой"): command_name = "кто такой"
    elif text.startswith("профиль"): command_name = "профиль"
    
    target_user_id, _ = await get_target_id(message, command_name)
    
    # Если это ответ на сообщение и target_user_id еще не найден
    if not target_user_id and message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    
    # Если цель все еще не найдена, показываем профиль отправителя
    if not target_user_id:
        target_user_id = message.from_user.id
        
    await get_user_profile(message, target_user_id)

@router.message(F.text.lower().in_({"награды", "мои награды"}))
async def handle_my_awards_command(message: types.Message):
    """
    Показывает награды отправителя сообщения.
    """
    target_user_id = message.from_user.id
    target_mention = await get_mention_by_id(target_user_id)
    
    awards = await get_awards(message.chat.id, target_user_id)
    if not awards:
        await message.answer(f"🏆 У вас пока нет наград.", parse_mode="HTML")
        return
        
    response = f"🏆 <b>Ваши награды ({target_mention}):</b>\n\n"
    for i, award in enumerate(awards, 1):
        from_mention = await get_mention_by_id(award["from_id"])
        response += f"награда [{i}] | {award['text']} (от {from_mention})\n"
    
    response += f"\nЧтобы убрать награду, используйте:\n<code>-награда (номер)</code>"
    
    await message.answer(response, parse_mode="HTML")
