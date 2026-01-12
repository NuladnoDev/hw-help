import aiohttp
from aiogram import Router, types, F
import logging
from bot.utils.filters import ModuleEnabledFilter

router = Router()

# Фильтр для проверки, что команда отправлена в группе или супергруппе и модуль включен
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("weather"))

async def get_weather(city: str):
    """Получает погоду через wttr.in с принудительным русским форматом."""
    # Используем формат m (метрический) и принудительный русский язык
    # А также убираем лишние детали для более точного парсинга
    url = f"https://wttr.in/{city}?format=j1&lang=ru"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                return None
        except Exception as e:
            logging.error(f"Ошибка при получении погоды: {e}")
            return None

@router.message(F.text.lower().startswith("погода"))
async def handle_weather_command(message: types.Message):
    """Обработчик команды погоды."""
    args = message.text.split(maxsplit=1)
    
    city = "Moscow"
    if len(args) > 1:
        city = args[1].strip()
    
    # Пытаемся получить данные
    weather_data = await get_weather(city)
    
    if not weather_data:
        await message.reply("❌ Не удалось найти такой город. Попробуйте написать название точнее.")
        return

    try:
        current = weather_data['current_condition'][0]
        temp = current['temp_C']
        feels_like = current['FeelsLikeC']
        
        # Получаем описание
        desc = current['lang_ru'][0]['value'].capitalize()
        
        # Исправления для странных переводов
        corrections = {
            "Близзард": "Метель",
            "Патчи": "Местами",
            "Свет": "Легкий",
            "Душ": "Ливень",
            "Переохлаждённый туман": "Ледяной туман"
        }
        for eng, rus in corrections.items():
            desc = desc.replace(eng, rus)

        humidity = current['humidity']
        wind_speed = current['windspeedKmph']
        
        # Логика отображения названия города
        # Если пользователь ввел город по-русски, используем его ввод для красоты
        if city.lower() in ["gawan", "гавань"]:
            city_display = "Гавань"
            desc = "Осадки в виде мальчонки"
        elif any(c in city for c in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"):
            city_display = city.capitalize()
        else:
            # Если ввел на английском, берем из ответа API
            area = weather_data['nearest_area'][0]
            city_display = area['areaName'][0]['value']

        text = (
            f"🌡 <b>Погода в г. {city_display}</b>\n\n"
            f"● Состояние: {desc}\n"
            f"● Температура: {temp}°C (ощущается как {feels_like}°C)\n"
            f"● Влажность: {humidity}%\n"
            f"● Ветер: {wind_speed} км/ч"
        )
        
        await message.reply(text, parse_mode="HTML")
        
    except (KeyError, IndexError) as e:
        logging.error(f"Ошибка парсинга погоды: {e}")
        await message.reply("❌ Ошибка при обработке данных о погоде.")
