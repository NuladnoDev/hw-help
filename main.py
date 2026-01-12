import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from bot.config_reader import config
from bot.handlers import admin, groups, user
from bot.middlewares import ActivityMiddleware, AntispamMiddleware

async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    # Оптимизация сессии для Windows (WinError 121)
    # Используем увеличенный таймаут (в секундах)
    session = AiohttpSession(
        timeout=60
    )
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=config.bot_token.get_secret_value(),
        session=session,
        default=DefaultBotProperties(parse_mode="HTML") # Устанавливаем HTML по умолчанию
    )
    dp = Dispatcher()

    # Регистрация middleware
    dp.message.outer_middleware(ActivityMiddleware())
    dp.message.outer_middleware(AntispamMiddleware())

    # Регистрация роутеров
    dp.include_router(admin.router)
    dp.include_router(groups.router)
    dp.include_router(user.router)

    # Запуск бота
    try:
        print("Бот запущен...")
        # Ограничиваем типы обновлений, чтобы бот не получал лишнего
        await dp.start_polling(
            bot, 
            allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"]
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Бот остановлен!")
