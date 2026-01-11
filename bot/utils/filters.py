import logging
import asyncio
from aiogram import types
from aiogram.filters import BaseFilter
from typing import Union
from bot.config_reader import config

from bot.utils.db_manager import get_rank, RANKS, get_user_rank_context, get_disabled_modules

class AdminFilter(BaseFilter):
    """
    Фильтр для проверки, является ли пользователь администратором в Telegram.
    """
    async def __call__(self, event: Union[types.Message, types.CallbackQuery]) -> bool:
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            chat = event.chat
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
            chat = event.message.chat
        else:
            return False

        if config.creator_id and user_id == config.creator_id:
            return True

        if not chat.type in ["group", "supergroup"]:
            return False

        try:
            member = await event.bot.get_chat_member(chat.id, user_id)
            return member.status in ["administrator", "creator"]
        except Exception as e:
            logging.error(f"Ошибка в RankFilter: {e}")
            return False

class ModuleEnabledFilter(BaseFilter):
    """
    Фильтр для проверки, включен ли модуль в данной группе.
    """
    def __init__(self, module_id: str):
        self.module_id = module_id

    async def __call__(self, event: Union[types.Message, types.CallbackQuery]) -> bool:
        chat_id = event.chat.id if isinstance(event, types.Message) else event.message.chat.id
        disabled_modules = await get_disabled_modules(chat_id)
        
        if self.module_id in disabled_modules:
            # Если это сообщение, можно ответить, что модуль выключен
            if isinstance(event, types.Message):
                # Здесь можно ничего не отвечать, чтобы бот просто игнорировал команду
                pass
            return False
            
        return True

class RankFilter(BaseFilter):
    """
    Фильтр для проверки минимального ранга пользователя в боте.
    """
    def __init__(self, min_rank: int):
        self.min_rank = min_rank

    async def __call__(self, event: Union[types.Message, types.CallbackQuery]) -> bool:
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            chat = event.chat
            message = event
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
            chat = event.message.chat
            message = event.message
        else:
            return False

        # Проверка ранга через централизованную функцию
        rank_level, _, _ = await get_user_rank_context(user_id, chat)
        
        if rank_level >= self.min_rank:
            return True
            
        # Если ранг недостаточен и это сообщение, отправляем уведомление
        if isinstance(event, types.Message):
            # Проверяем, не отправляли ли мы уже уведомление для этого сообщения
            # Используем ID сообщения как ключ, чтобы точно избежать дублей
            msg_id = f"rank_notified_{event.message_id}"
            if hasattr(event.bot, msg_id):
                return False
                
            required_name = RANKS.get(self.min_rank, "Неизвестно")
            try:
                await event.reply(
                    f"⚠️ Эта команда доступна с ранга [{self.min_rank}] <b>{required_name}</b>",
                    parse_mode="HTML"
                )
                # Помечаем в боте, что это сообщение уже обработано (на время жизни объекта бота)
                setattr(event.bot, msg_id, True)
                
                # Удаляем метку через 5 секунд, чтобы не забивать память
                async def clear_notif():
                    await asyncio.sleep(5)
                    if hasattr(event.bot, msg_id):
                        delattr(event.bot, msg_id)

                asyncio.create_task(clear_notif())
                
            except Exception as e:
                logging.error(f"Ошибка при отправке уведомления о ранге: {e}")
            
        return False

async def is_admin(message: types.Message) -> bool:
    """
    Утилита для ручной проверки прав.
    """
    filter_obj = AdminFilter()
    return await filter_obj(message)
