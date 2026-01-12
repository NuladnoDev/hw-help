from PIL import Image, ImageDraw, ImageFont
import os
import re
import random

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

def generate_modern_activity_chart():
    width, height = 800, 450
    bg_color = (255, 255, 255)
    accent_color = (255, 120, 0) # Оранжевый
    grid_color = (245, 245, 245) # Очень светлая сетка
    text_color = (40, 40, 40)
    
    # Создаем холст
    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    title_font = get_font(30)
    label_font = get_font(14)
    value_font = get_font(12)

    # Рисуем заголовок
    title = "АКТИВНОСТЬ ЗА 30 ДНЕЙ"
    draw.text((40, 30), title, font=title_font, fill=text_color)
    draw.line([(40, 75), (140, 75)], fill=accent_color, width=5)

    # Генерируем тестовые данные
    data = [random.randint(5, 100) for _ in range(30)]
    max_val = max(data)
    
    # Параметры графика
    margin_left = 60
    margin_bottom = 70
    plot_width = width - margin_left - 40
    plot_height = height - 160
    bar_spacing = plot_width / len(data)
    bar_width = bar_spacing * 0.75
    
    # Рисуем горизонтальную сетку
    steps = 5
    for i in range(steps + 1):
        y = height - margin_bottom - (i * plot_height / steps)
        draw.line([(margin_left, y), (width - 40, y)], fill=grid_color, width=1)
        # Значения слева
        val = int(i * max_val / steps)
        draw.text((15, y - 8), str(val), font=value_font, fill=(180, 180, 180))

    # Рисуем столбики
    for i, val in enumerate(data):
        h = (val / max_val) * plot_height if max_val > 0 else 0
        x0 = margin_left + i * bar_spacing
        y0 = height - margin_bottom - h
        x1 = x0 + bar_width
        y1 = height - margin_bottom
        
        if h > 2:
            draw.rounded_rectangle([x0, y0, x1, y1], radius=6, fill=accent_color)
        else:
            draw.rounded_rectangle([x0, y1-3, x1, y1], radius=2, fill=(230, 230, 230))

    # Подписи дат
    for i in range(0, 31, 5):
        x = margin_left + i * bar_spacing
        draw.text((x, height - margin_bottom + 15), f"{i+1} янв", font=label_font, fill=(160, 160, 160))

    # Сохраняем
    img.save("activity_new_preview.png")
    print("Новый дизайн сгенерирован: activity_new_preview.png")

if __name__ == "__main__":
    generate_modern_activity_chart()
