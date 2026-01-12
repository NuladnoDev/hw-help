import aiohttp
import logging
import re

async def get_random_joke() -> str:
    """
    Получает случайный анекдот с rzhunemogu.ru.
    API возвращает некорректный JSON (неэкранированные кавычки),
    поэтому используем регулярные выражения для извлечения текста.
    """
    url = "http://rzhunemogu.ru/RandJSON.aspx?CType=1"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    # API возвращает текст в кодировке Windows-1251
                    content = await response.read()
                    text = content.decode('cp1251', errors='ignore')
                    
                    # Извлекаем содержимое между {"content":" и "}
                    # Используем DOTALL, чтобы захватывать переносы строк
                    match = re.search(r'{"content":"(.*?)"}', text, re.DOTALL)
                    if match:
                        joke = match.group(1).strip()
                        # Очищаем от возможных артефактов
                        joke = joke.replace('\\r\\n', '\n').replace('\\n', '\n')
                        return joke
                return "❌ Не удалось получить анекдот. Попробуйте позже."
        except Exception as e:
            logging.error(f"Ошибка при получении анекдота: {e}")
            return "❌ Произошла ошибка при поиске анекдота."
