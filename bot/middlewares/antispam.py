from typing import Any, Awaitable, Callable, Dict
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.utils.db_manager import is_user_blacklisted, get_disabled_modules

class AntispamMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем только сообщения в группах
        if not isinstance(event, Message) or not event.chat.type in ["group", "supergroup"]:
            return await handler(event, data)

        # Проверяем, не бот ли это
        if not event.from_user or event.from_user.is_bot:
            return await handler(event, data)

        # Проверяем, включен ли модуль антиспама в этом чате
        disabled_modules = await get_disabled_modules(event.chat.id)
        if "antispam" in disabled_modules:
            return await handler(event, data)

        # Проверка на наличие в черном списке
        if await is_user_blacklisted(event.from_user.id):
            try:
                # Пытаемся забанить и удалить сообщение
                await event.chat.ban(user_id=event.from_user.id)
                await event.delete()
                return # Прерываем выполнение, дальше не идем
            except Exception as e:
                logging.error(f"Ошибка при бане спамера в middleware: {e}")
                # Если не удалось забанить (например, нет прав), просто продолжаем
                return await handler(event, data)

        return await handler(event, data)
