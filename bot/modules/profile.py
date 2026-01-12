from aiogram import types
from bot.utils.db_manager import (
    get_mention_by_id, get_user_rank_context,
    get_user_profile_data, get_group_rank_name,
    get_user_activity_series, get_user_activity_summary,
    get_user_clan, get_user_clubs, get_user_reputation
)
from bot.keyboards.profile_keyboards import get_profile_kb
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

def get_relative_time(dt: datetime) -> str:
    """
    Возвращает строку вида '2 дня назад' или '5 минут назад'.
    """
    # Гарантируем, что оба времени имеют информацию о часовом поясе
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return "только что"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} мин. назад"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} ч. назад"
    else:
        days = seconds // 86400
        return f"{days} дн. назад"

async def generate_activity_chart(user_id: int, days: int = 30) -> Optional[BytesIO]:
    series = await get_user_activity_series(user_id, days=days)
    # Если данных вообще нет или все значения по нулям, создаем пустой график вместо None
    if not series:
        return None
    
    max_count = max(count for _, count in series) or 0
    # Даже если активность нулевая, мы все равно рисуем пустую сетку, чтобы картинка была
    # if max_count == 0:
    #     return None
    
    def get_font(size=14):
        # Пути к шрифтам на Linux (хост) и Windows (локально)
        fonts = [
            "bot/assets/fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "arial.ttf"
        ]
        for f in fonts:
            try:
                return ImageFont.truetype(f, size)
            except:
                continue
        return ImageFont.load_default()

    width, height = 800, 400
    margin_left, margin_right, margin_top, margin_bottom = 40, 75, 40, 60
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    grid_color = (235, 235, 235)
    axis_color = (120, 120, 120)
    bar_color = (255, 140, 0)
    
    font = get_font(14)
    title_font = get_font(18)
    label_font = get_font(14)
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
    
    title = "Статистика активности"
    # Исправление для новых версий Pillow (textsize удален)
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((width - tw) / 2, 10), title, fill=axis_color, font=title_font)
    
    y_label = "Сообщения"
    # Создаем временное изображение для поворота текста
    l_bbox = draw.textbbox((0, 0), y_label, font=label_font)
    l_w = l_bbox[2] - l_bbox[0]
    l_h = l_bbox[3] - l_bbox[1]
    
    # Рисуем вертикально справа (после чисел)
    txt_img = Image.new("RGBA", (l_w, l_h + 5), (255, 255, 255, 0))
    d = ImageDraw.Draw(txt_img)
    d.text((0, 0), y_label, fill=axis_color, font=label_font)
    rotated = txt_img.rotate(90, expand=True)
    img.paste(rotated, (width - 30, margin_top + (plot_height - l_w) // 2), rotated)
    
    n = len(series)
    if n == 0:
        return None
    
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
        
        if idx % max(1, n // 10) == 0:
            label = day.strftime("%d.%m")
            bbox = draw.textbbox((0, 0), label, font=font)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            draw.text((x_center - lw / 2, height - margin_bottom + 5), label, fill=axis_color, font=font)
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def get_user_profile(message: types.Message, target_user_id: int):
    """
    Формирует и отправляет профиль пользователя в новом формате.
    Оптимизировано для быстрой работы.
    """
    # 1. Сначала получаем все данные из БД одним пакетом
    db_data = await get_user_profile_data(target_user_id, message.chat.id)
    
    # 2. Пытаемся получить информацию из Telegram (только если нужно)
    try:
        # Используем кэш из db_data, если там есть ник
        display_name = db_data.get("nickname")
        
        # Если в чате, пробуем получить актуальное имя
        member = await message.chat.get_member(target_user_id)
        user = member.user
        
        if not display_name:
            display_name = f"@{user.username}" if user.username else user.full_name
            
        user_mention = user.mention_html(display_name)
        
        # Проверяем на создателя чата для ранга
        if member.status == "creator" and db_data["rank_level"] < 5:
            db_data["rank_level"] = 5
            
    except Exception:
        # Если не удалось получить инфо из Telegram, используем get_mention_by_id (он тоже лезет в БД, но это крайний случай)
        user_mention = await get_mention_by_id(target_user_id)

    # 3. Получаем название ранга с учетом падежа (может быть в кэше БД)
    rank_name = await get_group_rank_name(message.chat.id, db_data["rank_level"], "nom")
    
    # 4. Получаем статистику активности текстом
    stats = await get_user_activity_summary(target_user_id)
    
    # 5. Получаем репутацию
    rep_data = await get_user_reputation(message.chat.id, target_user_id)
    
    # Форматирование дат
    first_app_dt = datetime.fromisoformat(db_data["first_appearance"])
    first_app_str = first_app_dt.strftime("%d.%m.%Y")
    
    last_msg_dt = datetime.fromisoformat(db_data["last_message"])
    last_active_str = get_relative_time(last_msg_dt)
    
    profile_text = f"👤 Это пользователь {user_mention}\n\n"
    profile_text += (
        f"🎖 <b>Ранг:</b> {rank_name}\n"
        f"💰 <b>Койнов на счету:</b> soon\n\n"
    )

    profile_text += f"✨ <b>{rep_data['points']}</b> [ ➕ {rep_data['plus_count']} | ➖ {rep_data['minus_count']} ]\n"

    # Город пока не отображаем, но данные сохраняем в db_data
    # if db_data.get("city"):
    #     profile_text += f"🏙 <b>Город:</b> {db_data['city']}\n"

    marriage = db_data.get("marriage")
    if marriage:
        partner_id = [p for p in marriage["partners"] if p != target_user_id][0]
        partner_mention = await get_mention_by_id(partner_id)
        profile_text += f"💍 <b>В браке с:</b> {partner_mention}\n"

    # Клан и кружки
    clan = await get_user_clan(message.chat.id, target_user_id)
    if clan:
        profile_text += f"🛡 <b>Клан:</b> {clan['name']}\n"
    
    clubs = await get_user_clubs(message.chat.id, target_user_id)
    if clubs:
        clubs_str = ", ".join([c["name"] for c in clubs])
        profile_text += f"🎨 <b>Кружки:</b> {clubs_str}\n"

    profile_text += (
        f"📅 <b>Впервые замечен:</b> {first_app_str}\n"
        f"⏳ <b>Последний актив:</b> {last_active_str}\n\n"
        f"📈 <b>Актив (д|н|м|весь):</b> {stats['day']} | {stats['week']} | {stats['month']} | {stats['total']}"
    )
    
    chart = await generate_activity_chart(target_user_id)
    
    if chart:
        photo = types.BufferedInputFile(chart.getvalue(), filename=f"chart_{target_user_id}.png")
        await message.answer_photo(
            photo=photo,
            caption=profile_text,
            parse_mode="HTML",
            reply_markup=get_profile_kb(target_user_id, has_quote=bool(db_data.get("quote")))
        )
    else:
        await message.answer(
            profile_text,
            parse_mode="HTML",
            reply_markup=get_profile_kb(target_user_id, has_quote=bool(db_data.get("quote")))
        )
