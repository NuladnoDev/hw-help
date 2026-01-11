from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.utils.db_manager import update_user_cache, update_user_activity

class ActivityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Это "внешний" middleware или "внутренний"? 
        # Если мы зарегистрируем его как message.middleware, он будет срабатывать ТОЛЬКО если найден хендлер.
        
        if isinstance(event, Message) and event.from_user:
            # Обновляем кэш и активность только когда пользователь реально взаимодействует с ботом
            update_user_cache(event.from_user.id, event.from_user.username, event.from_user.full_name)
            update_user_activity(event.from_user.id)
            
        return await handler(event, data)
