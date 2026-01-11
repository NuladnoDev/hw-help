import logging
import asyncio
from aiogram import types
from aiogram.filters import BaseFilter
from typing import Union
from bot.config_reader import config

from bot.utils.db_manager import (
    get_user_rank_context, RANKS,
    get_disabled_modules, get_permission_settings
)

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
    Фильтр для проверки ранга пользователя в БД.
    Поддерживает динамическую проверку прав из БД.
    """
    def __init__(self, min_rank: int = None, action_id: str = None):
        self.min_rank = min_rank
        self.action_id = action_id

    async def __call__(self, event: Union[types.Message, types.CallbackQuery]) -> bool:
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            chat = event.chat
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
            chat = event.message.chat
        else:
            return False

        if not chat.type in ["group", "supergroup"]:
            return False

        # Получаем ранг пользователя
        user_rank, _, _ = await get_user_rank_context(user_id, chat)
        
        # Определяем требуемый ранг
        required_rank = self.min_rank
        
        # Если задан action_id, проверяем настройки группы в БД
        if self.action_id:
            settings = await get_permission_settings(chat.id)
            if self.action_id in settings:
                required_rank = settings[self.action_id]
        
        # Если ранг все еще не определен (ни min_rank, ни в БД), пропускаем
        if required_rank is None:
            return True
            
        result = user_rank >= required_rank
        
        # Если ранг недостаточен и это сообщение, уведомляем
        if not result and isinstance(event, types.Message):
            required_name = RANKS.get(required_rank, "Неизвестно")
            await event.reply(
                f"⚠️ Эта команда доступна с ранга [{required_rank}] <b>{required_name}</b>",
                parse_mode="HTML"
            )
            
        return result

async def is_admin(message: types.Message) -> bool:
    """
    Утилита для ручной проверки прав.
    """
    filter_obj = AdminFilter()
    return await filter_obj(message)
