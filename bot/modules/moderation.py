from aiogram import types
from aiogram.exceptions import TelegramBadRequest
import logging
import time

async def delete_messages(message: types.Message, count: int = 1):
    """
    Функция для удаления сообщений в чате.
    """
    chat_id = message.chat.id
    current_time = time.time()
    deleted_count = 0
    
    # Максимальный возраст сообщения для удаления (48 часов)
    MAX_AGE = 48 * 3600

    if message.reply_to_message:
        start_id = message.reply_to_message.message_id
        # Проверяем возраст первого сообщения
        if current_time - message.reply_to_message.date.timestamp() > MAX_AGE:
            await message.reply("❌ Сообщения старше 48 часов нельзя удалить.")
            return

        for i in range(count):
            try:
                await message.bot.delete_message(chat_id, start_id + i)
                deleted_count += 1
            except TelegramBadRequest as e:
                if "message can't be deleted" in e.message.lower():
                    # Вероятно, сообщение слишком старое или уже удалено
                    break
                logging.warning(f"Не удалось удалить сообщение {start_id + i}: {e}")
            except Exception as e:
                logging.error(f"Ошибка при удалении: {e}")
    else:
        # Удаляем сообщение с командой
        try:
            await message.bot.delete_message(chat_id, message.message_id)
            deleted_count += 1
        except Exception:
            pass

        # Пытаемся удалить предыдущие сообщения
        for i in range(1, count):
            try:
                # В этом режиме мы не знаем точно, существуют ли сообщения, 
                # поэтому просто пробуем удалять по убыванию ID
                await message.bot.delete_message(chat_id, message.message_id - i)
                deleted_count += 1
            except TelegramBadRequest:
                continue
            except Exception as e:
                logging.error(f"Ошибка при удалении: {e}")
    
    # Отправляем уведомление, которое само удалится через несколько секунд
    confirm_msg = await message.answer(f"🗑️ Удалено {deleted_count} сообщений.")
    import asyncio
    await asyncio.sleep(3)
    try:
        await confirm_msg.delete()
    except Exception:
        pass
