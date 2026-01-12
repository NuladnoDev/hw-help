from aiogram import Router, types, F
from bot.utils.db_manager import add_antispam_report, is_user_blacklisted
from bot.utils.filters import ModuleEnabledFilter
import logging

router = Router()
# Применяем фильтр модуля ко всему роутеру
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("antispam"))
router.chat_member.filter(ModuleEnabledFilter("antispam"))

@router.message(F.text.lower().startswith(".жб антиспам"))
async def handle_antispam_report(message: types.Message):
    """Обрабатывает жалобу на спам."""
    target_user = None
    
    # 1. Определяем цель (реплей или упоминание)
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        # Ищем упоминание в тексте
        if message.entities:
            for entity in message.entities:
                if entity.type == "text_mention":
                    target_user = entity.user
                    break
                # Обычные @mentions без ID получить сложнее без кэша всех юзеров, 
                # поэтому пока приоритет на реплеи и текстовые упоминания.
    
    if not target_user:
        await message.reply(
            "❌ Вы должны ответить на сообщение спамера или упомянуть его.\n"
            "Использование: <code>.жб антиспам</code> (в ответ на сообщение)"
        , parse_mode="HTML")
        return

    if target_user.id == message.from_user.id:
        await message.reply("❌ Нельзя жаловаться на самого себя.")
        return

    if target_user.is_bot:
        return

    # 2. Добавляем жалобу в БД
    res = await add_antispam_report(message.from_user.id, target_user.id, message.chat.id)
    
    if res["status"] == "limit_exceeded":
        await message.reply("❌ Вы уже подавали жалобу за последние 24 часа. Лимит: 1 жалоба в сутки.")
        return
    
    if res["status"] == "error":
        await message.reply("❌ Произошла ошибка при подаче жалобы.")
        return

    count = res["count"]
    await message.answer(
        f"✅ Жалоба принята. Это {count}-я жалоба на этого пользователя.\n"
        f"При достижении 5 жалоб он будет занесен в глобальный черный список HW-антиспам."
    )

    # 3. Если пользователь только что попал в ЧС — кикаем его
    if res.get("is_blacklisted"):
        try:
            await message.chat.ban(user_id=target_user.id)
            await message.answer(
                f"🚫 Пользователь {target_user.full_name} набрал 5 жалоб и внесен в <b>глобальный черный список HW-антиспам</b>.\n"
                f"Он был исключен из этого чата.",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Не удалось кикнуть спамера: {e}")

@router.message()
async def check_for_spammers(message: types.Message):
    """Проверяет каждого отправителя сообщения на наличие в черном списке."""
    if not message.from_user or message.from_user.is_bot:
        return

    if await is_user_blacklisted(message.from_user.id):
        try:
            await message.chat.ban(user_id=message.from_user.id)
            await message.delete()
        except Exception:
            pass

@router.chat_member()
async def on_user_join(event: types.ChatMemberUpdated):
    """Проверяет вступающих пользователей."""
    # Проверяем только если пользователь вступил или был разбанен
    if event.new_chat_member.status in ["member", "administrator"]:
        user_id = event.new_chat_member.user.id
        if await is_user_blacklisted(user_id):
            try:
                await event.chat.ban(user_id=user_id)
                # Опционально: написать в чат, почему кикнули
            except Exception:
                pass
