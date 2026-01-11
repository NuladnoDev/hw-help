from datetime import timedelta
import re

def parse_duration(duration_str: str) -> timedelta | None:
    """
    Парсит строку продолжительности (например, "10м", "2ч", "3д") в объект timedelta.
    Возвращает None, если строка не может быть распарсена.
    """
    if not duration_str:
        return None

    total_seconds = 0
    
    # Дни
    days_match = re.search(r'(\d+)(д|d)', duration_str, re.IGNORECASE)
    if days_match:
        total_seconds += int(days_match.group(1)) * 24 * 3600
        duration_str = duration_str.replace(days_match.group(0), '')

    # Часы
    hours_match = re.search(r'(\d+)(ч|h)', duration_str, re.IGNORECASE)
    if hours_match:
        total_seconds += int(hours_match.group(1)) * 3600
        duration_str = duration_str.replace(hours_match.group(0), '')

    # Минуты
    minutes_match = re.search(r'(\d+)(м|m)', duration_str, re.IGNORECASE)
    if minutes_match:
        total_seconds += int(minutes_match.group(1)) * 60
        duration_str = duration_str.replace(minutes_match.group(0), '')
    
    # Если ничего не распарсили, или остались лишние символы, возвращаем None
    if total_seconds == 0 or duration_str.strip():
        return None

    return timedelta(seconds=total_seconds)

