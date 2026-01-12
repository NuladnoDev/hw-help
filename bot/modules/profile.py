from aiogram import types
from bot.utils.db_manager import (
    get_mention_by_id, get_user_rank_context,
    get_user_profile_data, get_group_rank_name,
    get_user_activity_series, get_user_activity_summary,
    get_user_clan, get_user_clubs, get_user_reputation,
    get_user_balance, get_user_level
)
from bot.keyboards.profile_keyboards import get_profile_kb
from datetime import datetime, timezone
from io import BytesIO
import os
import re
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

def get_font(size=14):
    """
    Максимально надежный поиск шрифта с поддержкой кириллицы.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
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
    if not series:
        return None
    
    max_count = max(count for _, count in series) or 0
    
    width, height = 800, 450
    margin_left, margin_right, margin_top, margin_bottom = 60, 40, 80, 70
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    
    # Светлая тема
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    
    grid_color = (245, 245, 245)
    axis_color = (180, 180, 180)
    bar_color = (255, 120, 0) # Оранжевый
    text_color = (40, 40, 40)
    
    title_font = get_font(30)
    label_font = get_font(14)
    grid_font = get_font(12)
    
    # Заголовок
    title = "АКТИВНОСТЬ ЗА 30 ДНЕЙ"
    draw.text((40, 25), title, fill=text_color, font=title_font)
    draw.line([(40, 65), (140, 65)], fill=bar_color, width=5)
    
    # Сетка
    steps = 5
    for i in range(steps + 1):
        y = margin_top + plot_height - int(plot_height * i / steps)
        draw.line([(margin_left, y), (width - margin_right, y)], fill=grid_color, width=1)
        
        val = int(max_count * i / steps) if max_count > 0 else 0
        draw.text((15, y - 8), str(val), fill=axis_color, font=grid_font)
    
    n = len(series)
    bar_spacing = plot_width / max(n, 1)
    bar_width = max(4, int(bar_spacing * 0.75))
    
    for idx, (day, count) in enumerate(series):
        x_center = margin_left + int(bar_spacing * idx + bar_spacing / 2)
        h = int((count / max_count) * plot_height) if max_count > 0 else 0
        
        x0 = x_center - bar_width // 2
        x1 = x_center + bar_width // 2
        y1 = margin_top + plot_height
        y0 = y1 - h
        
        if h > 2:
            # Чистый оранжевый столбик со скруглением сверху
            draw.rounded_rectangle([x0, y0, x1, y1], radius=6, fill=bar_color)
        else:
            # Минимальная отметка для нулевой/малой активности
            draw.rounded_rectangle([x0, y1-3, x1, y1], radius=2, fill=(235, 235, 235))
            
        # Подписи дат (каждые 5 дней)
        if idx % 5 == 0:
            label = day.strftime("%d.%m")
            bbox = draw.textbbox((0, 0), label, font=label_font)
            lw = bbox[2] - bbox[0]
            draw.text((x_center - lw / 2, height - margin_bottom + 15), label, fill=axis_color, font=label_font)
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def generate_level_card_image(user_id: int, username: str) -> Optional[BytesIO]:
    level_data = await get_user_level(user_id)
    level = level_data["level"]
    xp = level_data["xp"]
    needed = level_data["needed_xp"]
    
    # Очистка имени от эмодзи для предотвращения квадратов
    display_username = clean_text(username)
    if not display_username:
        display_username = "User"

    width, height = 800, 400
    bg_color = (255, 255, 255)
    accent_color = (255, 120, 0)
    text_main = (40, 40, 40)
    text_secondary = (140, 140, 140)
    bar_bg = (245, 245, 245)
    
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
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
    
    # Дефолтный аватар
    draw.ellipse([av_x, av_y, av_x+avatar_size, av_y+avatar_size], fill=accent_color)
    letter = display_username[0].upper() if display_username else "?"
    bbox = draw.textbbox((0, 0), letter, font=font_avatar)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text((av_x+(avatar_size-tw)/2, av_y+(avatar_size-th)/2 - 8), letter, font=font_avatar, fill=(255, 255, 255))

    # Инфо
    info_x = av_x + avatar_size + 40
    draw.text((info_x, av_y + 10), display_username, font=font_name, fill=text_main)
    draw.text((info_x, av_y + 65), "УРОВЕНЬ", font=font_lvl_label, fill=text_secondary)
    draw.text((info_x, av_y + 85), str(level), font=font_lvl_val, fill=accent_color)
    
    # Прогресс-бар
    bar_x, bar_y = 50, 270
    bar_w, bar_h = 700, 55
    draw.rounded_rectangle([bar_x, bar_y, bar_x+bar_w, bar_y+bar_h], radius=28, fill=bar_bg)
    
    progress = min(1.0, xp / needed) if needed > 0 else 0
    if progress > 0:
        fill_w = int(bar_w * progress)
        fill_w = max(fill_w, 56)
        draw.rounded_rectangle([bar_x, bar_y, bar_x+fill_w, bar_y+bar_h], radius=28, fill=accent_color)
    
    xp_text = f"{xp} / {needed} XP"
    bbox = draw.textbbox((0, 0), xp_text, font=font_xp)
    tw = bbox[2]-bbox[0]
    draw.text((bar_x + (bar_w - tw)/2, bar_y + bar_h + 10), xp_text, font=font_xp, fill=text_secondary)

    buf = BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def get_user_profile(message: types.Message, target_user_id: int):
    """
    Формирует и отправляет профиль пользователя.
    """
    profile_text, has_quote = await build_profile_text(message, target_user_id)
    
    chart = await generate_activity_chart(target_user_id)
    
    if chart:
        photo = types.BufferedInputFile(chart.getvalue(), filename=f"chart_{target_user_id}.png")
        await message.answer_photo(
            photo=photo,
            caption=profile_text,
            parse_mode="HTML",
            reply_markup=get_profile_kb(target_user_id, has_quote=has_quote)
        )
    else:
        await message.answer(
            profile_text,
            parse_mode="HTML",
            reply_markup=get_profile_kb(target_user_id, has_quote=has_quote)
        )

async def build_profile_text(message: types.Message, target_user_id: int):
    """
    Строит текст профиля и признак наличия цитаты без отправки сообщения.
    Используется как для первого показа, так и для возврата из меню уровней.
    """
    db_data = await get_user_profile_data(target_user_id, message.chat.id)
    
    try:
        display_name = db_data.get("nickname")
        member = await message.chat.get_member(target_user_id)
        user = member.user
        
        if not display_name:
            display_name = f"@{user.username}" if user.username else user.full_name
            
        user_mention = user.mention_html(display_name)
        
        if member.status == "creator" and db_data["rank_level"] < 5:
            db_data["rank_level"] = 5
    except Exception:
        user_mention = await get_mention_by_id(target_user_id)
    
    rank_name = await get_group_rank_name(message.chat.id, db_data["rank_level"], "nom")
    stats = await get_user_activity_summary(target_user_id)
    rep_data = await get_user_reputation(message.chat.id, target_user_id)
    balance = await get_user_balance(target_user_id)
    
    first_app_dt = datetime.fromisoformat(db_data["first_appearance"])
    first_app_str = first_app_dt.strftime("%d.%m.%Y")
    
    last_msg_dt = datetime.fromisoformat(db_data["last_message"])
    last_active_str = get_relative_time(last_msg_dt)
    
    profile_text = f"👤 Это пользователь {user_mention}\n\n"
    profile_text += (
        f"🎖 <b>Ранг:</b> {rank_name}\n"
        f"💰 <b>Койнов:</b> <code>{balance}</code>\n\n"
    )
    
    profile_text += f"✨ <b>{rep_data['points']}</b> [ ➕ {rep_data['plus_count']} | ➖ {rep_data['minus_count']} ]\n"
    
    marriage = db_data.get("marriage")
    if marriage:
        partner_id = [p for p in marriage["partners"] if p != target_user_id][0]
        partner_mention = await get_mention_by_id(partner_id)
        profile_text += f"💍 <b>В браке с:</b> {partner_mention}\n"
    
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
    
    has_quote = bool(db_data.get("quote"))
    return profile_text, has_quote
