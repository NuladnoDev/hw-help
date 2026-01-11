from aiogram import Router, types, F
from aiogram.filters import ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated
from aiogram.enums import ChatMemberStatus
from bot.utils.db_manager import set_welcome_message, get_welcome_message
from bot.utils.filters import RankFilter

router = Router()

# Фильтр для настройки приветствия (+Приветствие)
@router.message(F.text.lower().startswith("+приветствие"), RankFilter(min_rank=3))
async def handle_set_welcome(message: types.Message):
    """
    Устанавливает приветствие для новых участников.
    Пример: +Приветствие Добро пожаловать, !Name!
    """
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            "❌ Вы не указали текст приветствия.\n"
            "Используйте: <code>+Приветствие (текст)</code>\n"
            "Доступные плейсхолдеры: <code>!Name</code> (имя пользователя)",
            parse_mode="HTML"
        )
        return
    
    welcome_text = parts[1].strip()
    await set_welcome_message(message.chat.id, welcome_text)
    await message.reply(f"✅ Приветствие для этого чата установлено:\n\n{welcome_text}")

# Хендлер для вступления нового участника
@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=F.new_chat_member.status.in_({ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR})))
async def on_user_joined(event: ChatMemberUpdated):
    """
    Срабатывает, когда пользователь вступает в чат.
    """
    # Проверяем, что это именно вступление (а не смена прав)
    if event.old_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED, ChatMemberStatus.RESTRICTED]:
        welcome_template = await get_welcome_message(event.chat.id)
        
        if not welcome_template:
            return

        user = event.from_user
        # Заменяем плейсхолдер !Name на упоминание пользователя
        welcome_text = welcome_template.replace("!Name", user.full_name)
        
        await event.bot.send_message(
            event.chat.id,
            welcome_text,
            parse_mode="HTML"
        )
