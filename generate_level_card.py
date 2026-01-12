import os
import re
from PIL import Image, ImageDraw, ImageFont

def get_font(size=14):
    """
    Максимально надежный поиск шрифта с поддержкой кириллицы.
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Список путей для проверки (в порядке приоритета)
    font_paths = [
        # 1. Твой шрифт в проекте
        os.path.join(project_root, "bot", "assets", "fonts", "arial.ttf"),
        # 2. Системные Windows
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\tahoma.ttf",
        # 3. Системные Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        # 4. Просто по имени (если в PATH)
        "arial.ttf",
        "DejaVuSans.ttf"
    ]
    
    for path in font_paths:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except:
            continue
            
    # Если совсем всё плохо - дефолт
    return ImageFont.load_default()

def clean_text(text: str) -> str:
    """
    Оставляет только то, что точно отобразится (латиница, кириллица, цифры).
    """
    if not text:
        return "User"
    # Оставляем: a-z, A-Z, а-я, А-Я, ё, Ё, 0-9 и базовые знаки
    cleaned = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s.,!@#$%^&*()\-+=?<>:;\[\]{}|\'\"\\/`~]', '', text)
    result = cleaned.strip()
    return result if result else "User"

def create_level_card(username="Pavel Durov 🌟", level=5, current_xp=150, needed_xp=300, has_avatar=False):
    # Размеры изображения
    width = 800
    height = 400
    
    # Цвета (Светлая тема)
    bg_color = (255, 255, 255)
    accent_color = (255, 120, 0)
    text_main = (40, 40, 40)
    text_secondary = (140, 140, 140)
    bar_bg = (245, 245, 245)
    
    # Очистка имени
    display_name = clean_text(username)
    
    # Создаем холст
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Шрифты
    font_name = get_font(42)
    font_lvl_label = get_font(24)
    font_lvl_val = get_font(80)
    font_xp = get_font(22)
    font_avatar = get_font(70)

    # Декор
    draw.ellipse([width-150, -50, width+50, 150], fill=(255, 120, 0, 30))
    
    # Аватар
    avatar_size = 160
    av_x, av_y = 50, 50
    draw.ellipse([av_x-2, av_y-2, av_x+avatar_size+2, av_y+avatar_size+2], outline=(240, 240, 240), width=2)
    
    # Дефолтный аватар с первой буквой
    draw.ellipse([av_x, av_y, av_x+avatar_size, av_y+avatar_size], fill=accent_color)
    letter = display_name[0].upper()
    bbox = draw.textbbox((0, 0), letter, font=font_avatar)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text((av_x+(avatar_size-tw)/2, av_y+(avatar_size-th)/2 - 8), letter, font=font_avatar, fill=(255, 255, 255))

    # Информация
    info_x = av_x + avatar_size + 40
    draw.text((info_x, av_y + 10), display_name, font=font_name, fill=text_main)
    draw.text((info_x, av_y + 65), "УРОВЕНЬ", font=font_lvl_label, fill=text_secondary)
    draw.text((info_x, av_y + 85), str(level), font=font_lvl_val, fill=accent_color)
    
    # Прогресс-бар
    bar_x, bar_y = 50, 270
    bar_w, bar_h = 700, 55
    draw.rounded_rectangle([bar_x, bar_y, bar_x+bar_w, bar_y+bar_h], radius=28, fill=bar_bg)
    
    progress = min(1.0, current_xp / needed_xp) if needed_xp > 0 else 0
    if progress > 0:
        fill_w = int(bar_w * progress)
        fill_w = max(fill_w, 56)
        draw.rounded_rectangle([bar_x, bar_y, bar_x+fill_w, bar_y+bar_h], radius=28, fill=accent_color)
    
    xp_text = f"{current_xp} / {needed_xp} XP"
    bbox = draw.textbbox((0, 0), xp_text, font=font_xp)
    tw = bbox[2]-bbox[0]
    draw.text((bar_x + (bar_w - tw)/2, bar_y + bar_h + 10), xp_text, font=font_xp, fill=text_secondary)

    # Сохранение
    image.save("level_card_preview.png")
    print(f"Готово! Карта сохранена в level_card_preview.png. Использовано имя: {display_name}")

if __name__ == "__main__":
    create_level_card()
