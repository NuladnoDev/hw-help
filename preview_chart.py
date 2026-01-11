import datetime
import random
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

def generate_preview_chart():
    # Имитация данных (30 дней)
    series = []
    today = datetime.date.today()
    for i in range(30):
        day = today - datetime.timedelta(days=29 - i)
        count = random.randint(0, 1000) if random.random() > 0.1 else 0
        series.append((day, count))
    
    max_count = max(count for _, count in series) or 0
    
    width, height = 800, 400
    margin_left, margin_right, margin_top, margin_bottom = 40, 75, 40, 60
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    
    grid_color = (235, 235, 235)
    axis_color = (120, 120, 120)
    bar_color = (255, 140, 0) # Оранжевый
    
    def get_font(size=14):
        fonts = ["arial.ttf", "C:\\Windows\\Fonts\\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        for f in fonts:
            try:
                return ImageFont.truetype(f, size)
            except:
                continue
        return ImageFont.load_default()

    font = get_font(14)
    title_font = get_font(18)
    grid_font = get_font(11)
    
    # Сетка и метки значений
    steps = 4
    for i in range(steps + 1):
        y = margin_top + int(plot_height * i / steps)
        draw.line([(margin_left, y), (width - margin_right, y)], fill=grid_color)
        
        # Значение справа (например: 1000, 750, 500, 250, 0)
        val = int(max_count * (steps - i) / steps) if max_count > 0 else 0
        val_str = str(val)
        v_bbox = draw.textbbox((0, 0), val_str, font=grid_font)
        v_h = v_bbox[3] - v_bbox[1]
        draw.text((width - margin_right + 5, y - v_h / 2), val_str, fill=axis_color, font=grid_font)
    
    title = "Статистика активности (Предпросмотр)"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) / 2, 10), title, fill=axis_color, font=title_font)
    
    # Вертикальная надпись "Сообщения" справа
    y_label = "Сообщения"
    l_bbox = draw.textbbox((0, 0), y_label, font=font)
    l_w = l_bbox[2] - l_bbox[0]
    l_h = l_bbox[3] - l_bbox[1]
    
    txt_img = Image.new("RGBA", (l_w, l_h + 5), (255, 255, 255, 0))
    d = ImageDraw.Draw(txt_img)
    d.text((0, 0), y_label, fill=axis_color, font=font)
    rotated = txt_img.rotate(90, expand=True)
    img.paste(rotated, (width - 30, margin_top + (plot_height - l_w) // 2), rotated)
    
    n = len(series)
    bar_spacing = plot_width / max(n, 1)
    bar_width = max(4, int(bar_spacing * 0.6))
    
    for idx, (day, count) in enumerate(series):
        x_center = margin_left + int(bar_spacing * idx + bar_spacing / 2)
        bar_height = int((count / max_count) * plot_height) if max_count > 0 else 0
        
        x0 = x_center - bar_width // 2
        x1 = x_center + bar_width // 2
        y1 = margin_top + plot_height
        y0 = y1 - bar_height
        
        draw.rectangle([x0, y0, x1, y1], fill=bar_color)
        
        # Подписи дат (каждая 3-я)
        if idx % 3 == 0:
            label = day.strftime("%d.%m")
            bbox = draw.textbbox((0, 0), label, font=font)
            lw = bbox[2] - bbox[0]
            draw.text((x_center - lw / 2, height - margin_bottom + 5), label, fill=axis_color, font=font)
    
    output_path = "preview_chart.png"
    img.save(output_path)
    print(f"Готово! График сохранен в файл: {output_path}")

if __name__ == "__main__":
    generate_preview_chart()
