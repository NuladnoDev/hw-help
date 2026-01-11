import json
import os
import time
from datetime import datetime
from aiogram import types
from bot.config_reader import config

# Кэш для активности, чтобы не писать в БД каждое сообщение
_activity_cache = {} # {user_id: last_update_timestamp}
_CACHE_TTL = 300 # 5 минут

DB_PATH = "banned_users.json"
MUTE_DB_PATH = "muted_users.json"
WARN_DB_PATH = "warns.json"
NICKNAME_DB_PATH = "nicknames.json"
DESCRIPTION_DB_PATH = "descriptions.json"
AWARDS_DB_PATH = "awards.json"
RANKS_DB_PATH = "ranks.json"
USER_STATS_PATH = "user_stats.json"
USER_CACHE_PATH = "users_cache.json"
INVITERS_DB_PATH = "inviters.json"
MARRIAGES_DB_PATH = "marriages.json"
RELATIONSHIPS_DB_PATH = "relationships.json"

def load_data(path=DB_PATH):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_data(data, path=DB_PATH):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_mute(chat_id, user_id, until_date=None):
    data = load_data(MUTE_DB_PATH)
    chat_key = str(chat_id)
    if chat_key not in data:
        data[chat_key] = {}
    data[chat_key][str(user_id)] = {
        "until": until_date.isoformat() if until_date else "permanent"
    }
    save_data(data, MUTE_DB_PATH)

def remove_mute(chat_id, user_id):
    data = load_data(MUTE_DB_PATH)
    chat_key = str(chat_id)
    if chat_key in data and str(user_id) in data[chat_key]:
        del data[chat_key][str(user_id)]
        save_data(data, MUTE_DB_PATH)

def is_user_muted(chat_id, user_id):
    data = load_data(MUTE_DB_PATH)
    chat_key = str(chat_id)
    user_key = str(user_id)
    if chat_key in data and user_key in data[chat_key]:
        mute_info = data[chat_key][user_key]
        if mute_info["until"] == "permanent":
            return True
        until_date = datetime.fromisoformat(mute_info["until"])
        if until_date > datetime.now():
            return True
        else:
            remove_mute(chat_id, user_id)
    return False

def update_user_cache(user_id, username, full_name=None):
    cache = load_data(USER_CACHE_PATH)
    # Сохраняем маппинг username -> id
    # Сохраняем маппинг id -> данные
    user_key = f"id_{user_id}"
    old_data = cache.get(user_key)
    
    # Если старые данные - строка (старый формат), превращаем в словарь
    if not isinstance(old_data, dict):
        current_username = old_data if isinstance(old_data, str) else None
        cache[user_key] = {"username": current_username}

    if username and username.strip():
        clean_username = username.replace("@", "").strip()
        cache[clean_username.lower()] = user_id
        cache[user_key]["username"] = clean_username
    if full_name and full_name.strip():
        cache[user_key]["full_name"] = full_name.strip()    
    save_data(cache, USER_CACHE_PATH)

def get_username_by_id(user_id):
    cache = load_data(USER_CACHE_PATH)
    data = cache.get(f"id_{user_id}")
    if isinstance(data, dict):
        return data.get("username")
    return data # Для обратной совместимости, если там была просто строка

def get_full_name_by_id(user_id):
    cache = load_data(USER_CACHE_PATH)
    data = cache.get(f"id_{user_id}")
    if isinstance(data, dict):
        return data.get("full_name")
    return None

def get_user_id_by_username(username):
    username = username.lower().replace("@", "")
    cache = load_data(USER_CACHE_PATH)
    return cache.get(username)

def add_ban(chat_id, user_id, until_date=None):
    data = load_data()
    chat_key = str(chat_id)
    if chat_key not in data:
        data[chat_key] = {}
    
    data[chat_key][str(user_id)] = {
        "until": until_date.isoformat() if until_date else "permanent"
    }
    save_data(data)

def remove_ban(chat_id, user_id):
    data = load_data()
    chat_key = str(chat_id)
    if chat_key in data and str(user_id) in data[chat_key]:
        del data[chat_key][str(user_id)]
        save_data(data)

def is_user_banned(chat_id, user_id):
    data = load_data()
    chat_key = str(chat_id)
    user_key = str(user_id)
    
    if chat_key in data and user_key in data[chat_key]:
        ban_info = data[chat_key][user_key]
        if ban_info["until"] == "permanent":
            return True
        
        until_date = datetime.fromisoformat(ban_info["until"])
        if until_date > datetime.now():
            return True
        else:
            # Срок бана истек, удаляем из базы
            remove_ban(chat_id, user_id)
    return False

def add_warn(chat_id, user_id, reason="Не указана", until_date=None):
    data = load_data(WARN_DB_PATH)
    chat_key = str(chat_id)
    user_key = str(user_id)
    
    if chat_key not in data:
        data[chat_key] = {}
    if user_key not in data[chat_key]:
        data[chat_key][user_key] = []
    
    warn_info = {
        "reason": reason,
        "date": datetime.now().isoformat(),
        "until": until_date.isoformat() if until_date else "permanent"
    }
    
    data[chat_key][user_key].append(warn_info)
    save_data(data, WARN_DB_PATH)
    return len(data[chat_key][user_key])

def get_warns(chat_id, user_id):
    data = load_data(WARN_DB_PATH)
    chat_key = str(chat_id)
    user_key = str(user_id)
    
    if chat_key not in data or user_key not in data[chat_key]:
        return []
    
    warns = data[chat_key][user_key]
    # Фильтруем просроченные варны
    active_warns = []
    current_time = datetime.now()
    
    for warn in warns:
        if warn["until"] == "permanent":
            active_warns.append(warn)
        else:
            until_date = datetime.fromisoformat(warn["until"])
            if until_date > current_time:
                active_warns.append(warn)
    
    if len(active_warns) != len(warns):
        data[chat_key][user_key] = active_warns
        save_data(data, WARN_DB_PATH)
        
    return active_warns

def remove_last_warn(chat_id, user_id):
    data = load_data(WARN_DB_PATH)
    chat_key = str(chat_id)
    user_key = str(user_id)
    
    if chat_key in data and user_key in data[chat_key] and data[chat_key][user_key]:
        data[chat_key][user_key].pop()
        save_data(data, WARN_DB_PATH)
        return True
    return False

def remove_warn_by_index(chat_id, user_id, index):
    """
    Удаляет предупреждение по индексу (0-based).
    """
    data = load_data(WARN_DB_PATH)
    chat_key = str(chat_id)
    user_key = str(user_id)
    
    if chat_key in data and user_key in data[chat_key]:
        warns = data[chat_key][user_key]
        if 0 <= index < len(warns):
            warns.pop(index)
            save_data(data, WARN_DB_PATH)
            return True
    return False

def clear_warns(chat_id, user_id):
    data = load_data(WARN_DB_PATH)
    chat_key = str(chat_id)
    user_key = str(user_id)
    
    if chat_key in data and user_key in data[chat_key]:
        data[chat_key][user_key] = []
        save_data(data, WARN_DB_PATH)
        return True
    return False

# --- Nicknames ---
def set_nickname(user_id, nickname):
    data = load_data(NICKNAME_DB_PATH)
    data[str(user_id)] = nickname
    save_data(data, NICKNAME_DB_PATH)

def remove_nickname(user_id):
    data = load_data(NICKNAME_DB_PATH)
    if str(user_id) in data:
        del data[str(user_id)]
        save_data(data, NICKNAME_DB_PATH)
        return True
    return False

def get_nickname(user_id):
    data = load_data(NICKNAME_DB_PATH)
    return data.get(str(user_id))

# --- Descriptions ---
def set_description(user_id, description):
    data = load_data(DESCRIPTION_DB_PATH)
    data[str(user_id)] = description
    save_data(data, DESCRIPTION_DB_PATH)

def remove_description(user_id):
    data = load_data(DESCRIPTION_DB_PATH)
    if str(user_id) in data:
        del data[str(user_id)]
        save_data(data, DESCRIPTION_DB_PATH)
        return True
    return False

def get_description(user_id):
    data = load_data(DESCRIPTION_DB_PATH)
    return data.get(str(user_id))

# --- Awards ---
def add_award(chat_id, target_user_id, admin_user_id, text):
    data = load_data(AWARDS_DB_PATH)
    c_id = str(chat_id)
    u_id = str(target_user_id)
    
    if c_id not in data:
        data[c_id] = {}
    if u_id not in data[c_id]:
        data[c_id][u_id] = []
    
    award_info = {
        "text": text,
        "from_id": admin_user_id,
        "date": datetime.now().isoformat()
    }
    data[c_id][u_id].append(award_info)
    save_data(data, AWARDS_DB_PATH)
    return len(data[c_id][u_id])

def get_awards(chat_id, user_id):
    data = load_data(AWARDS_DB_PATH)
    return data.get(str(chat_id), {}).get(str(user_id), [])

def remove_award_by_index(chat_id, user_id, index):
    """
    Удаляет награду по индексу (0-based) в конкретном чате.
    """
    data = load_data(AWARDS_DB_PATH)
    c_id = str(chat_id)
    u_id = str(user_id)
    
    if c_id in data and u_id in data[c_id]:
        awards = data[c_id][u_id]
        if 0 <= index < len(awards):
            awards.pop(index)
            save_data(data, AWARDS_DB_PATH)
            return True
    return False

# --- Ranks ---
RANKS = {
    1: "Обычный пользователь",
    2: "Младший модератор",
    3: "Модератор",
    4: "Администратор",
    5: "Создатель"
}

def get_rank(user_id, chat_id):
    """
    Возвращает числовой уровень ранга и его название для конкретного чата.
    1. Если user_id == creator_id из конфига — ранг 5 (глобально).
    2. Иначе берем из БД для конкретного chat_id.
    По умолчанию ранг 1.
    """
    # 1. Глобальный владелец бота
    if config.creator_id and user_id == config.creator_id:
        return 5, RANKS[5]
    
    data = load_data(RANKS_DB_PATH)
    chat_key = str(chat_id)
    user_key = str(user_id)
    
    if chat_key in data and user_key in data[chat_key]:
        rank_level = data[chat_key][user_key]
        # Минимальный ранг — 1
        if rank_level < 1:
            return 1, RANKS[1]
        return rank_level, RANKS.get(rank_level, "Неизвестно")
        
    return 1, RANKS[1]

async def get_user_rank_context(user_id, chat: types.Chat):
    """
    Определяет ранг пользователя и его 'супер-статус'.
    Централизованная функция для всех модулей (профиль, фильтры, управление).
    """
    # 1. Глобальный создатель
    if config.creator_id and user_id == config.creator_id:
        return 5, RANKS[5], True
        
    # 2. Проверяем статус в Telegram (Создатель чата)
    try:
        member = await chat.get_member(user_id)
        if member.status == "creator":
            return 5, RANKS[5], True
    except Exception:
        pass
    
    # 3. Обычный ранг из БД
    level, name = get_rank(user_id, chat.id)
    return level, name, False

async def can_user_modify_other(admin_user_id: int, target_user_id: int, chat: types.Chat) -> bool:
    """
    Проверяет, может ли один пользователь изменять другого согласно иерархии:
    - Супер-админ (создатель чата/бота) может изменять всех, кроме других супер-админов.
    - Обычный админ может изменять только тех, кто ниже его по рангу.
    - Себя изменять можно (для команд вроде 'кто я' или управления своим профилем, если применимо).
    """
    if admin_user_id == target_user_id:
        return True
        
    admin_rank, _, is_admin_super = await get_user_rank_context(admin_user_id, chat)
    target_rank, _, is_target_super = await get_user_rank_context(target_user_id, chat)
    
    if is_admin_super:
        # Супер-админ может изменять всех, кроме других супер-админов
        return not is_target_super
        
    # Обычный админ может изменять только тех, кто СТРОГО ниже по рангу
    return admin_rank > target_rank

def save_inviter(chat_id, user_id, inviter_id):
    """Сохраняет ID того, кто пригласил пользователя."""
    data = load_data(INVITERS_DB_PATH)
    chat_key = str(chat_id)
    if chat_key not in data:
        data[chat_key] = {}
    data[chat_key][str(user_id)] = inviter_id
    save_data(data, INVITERS_DB_PATH)

def get_inviter(chat_id, user_id):
    """Возвращает ID того, кто пригласил пользователя (или None)."""
    data = load_data(INVITERS_DB_PATH)
    return data.get(str(chat_id), {}).get(str(user_id))

def set_rank(user_id, chat_id, rank_level):
    """
    Устанавливает числовой уровень ранга пользователю в конкретном чате.
    """
    if rank_level not in RANKS or rank_level < 1:
        return False
    data = load_data(RANKS_DB_PATH)
    chat_key = str(chat_id)
    user_key = str(user_id)
    
    if chat_key not in data:
        data[chat_key] = {}
        
    data[chat_key][user_key] = rank_level
    save_data(data, RANKS_DB_PATH)
    return True

def get_all_ranked_users(chat_id):
    """
    Возвращает словарь {user_id: rank_level} для всех пользователей с рангами в конкретном чате.
    """
    data = load_data(RANKS_DB_PATH)
    return data.get(str(chat_id), {})

# --- Marriages ---
def create_marriage(user1_id, user2_id):
    data = load_data(MARRIAGES_DB_PATH)
    
    marriage_info = {
        "partners": [user1_id, user2_id],
        "created_at": datetime.now().isoformat()
    }
    
    # Сохраняем для обоих партнеров (глобально)
    data[str(user1_id)] = marriage_info
    data[str(user2_id)] = marriage_info
    save_data(data, MARRIAGES_DB_PATH)

def get_marriage(user_id):
    data = load_data(MARRIAGES_DB_PATH)
    return data.get(str(user_id))

def remove_marriage(user_id):
    data = load_data(MARRIAGES_DB_PATH)
    
    marriage = data.get(str(user_id))
    if not marriage:
        return False
        
    # Удаляем у обоих партнеров
    for partner_id in marriage["partners"]:
        if str(partner_id) in data:
            del data[str(partner_id)]
            
    save_data(data, MARRIAGES_DB_PATH)
    return True

# --- Relationships ---
def update_relationship(user1_id, user2_id, action_type):
    """
    Обновляет статистику отношений между двумя пользователями.
    """
    data = load_data(RELATIONSHIPS_DB_PATH)
    
    # Всегда сортируем ID, чтобы ключ был одинаковым для пары
    u1, u2 = sorted([int(user1_id), int(user2_id)])
    pair_key = f"{u1}:{u2}"
    
    if pair_key not in data:
        data[pair_key] = {
            "actions": {},
            "total_interactions": 0,
            "last_interaction": ""
        }
    
    # Обновляем счетчик конкретного действия
    actions = data[pair_key]["actions"]
    actions[action_type] = actions.get(action_type, 0) + 1
    
    data[pair_key]["total_interactions"] += 1
    data[pair_key]["last_interaction"] = datetime.now().isoformat()
    
    save_data(data, RELATIONSHIPS_DB_PATH)
    return data[pair_key]

def get_relationship(user1_id, user2_id):
    data = load_data(RELATIONSHIPS_DB_PATH)
    u1, u2 = sorted([int(user1_id), int(user2_id)])
    pair_key = f"{u1}:{u2}"
    return data.get(pair_key)

def delete_relationship(user1_id, user2_id):
    """
    Полностью удаляет историю отношений между двумя пользователями.
    """
    data = load_data(RELATIONSHIPS_DB_PATH)
    u1, u2 = sorted([int(user1_id), int(user2_id)])
    pair_key = f"{u1}:{u2}"
    
    if pair_key in data:
        del data[pair_key]
        save_data(data, RELATIONSHIPS_DB_PATH)
        return True
    return False

def get_all_user_relationships(user_id):
    """
    Возвращает список всех отношений пользователя с другими участниками.
    """
    data = load_data(RELATIONSHIPS_DB_PATH)
    user_id = int(user_id)
    results = []
    
    for pair_key, rel_data in data.items():
        u1, u2 = map(int, pair_key.split(":"))
        if u1 == user_id or u2 == user_id:
            partner_id = u2 if u1 == user_id else u1
            results.append({
                "partner_id": partner_id,
                "data": rel_data
            })
            
    # Сортируем по количеству взаимодействий (от большего к меньшему)
    results.sort(key=lambda x: x["data"]["total_interactions"], reverse=True)
    return results

# --- Mentions ---

def get_user_mention_with_nickname(user):
    """
    Возвращает HTML-упоминание пользователя с учетом его кастомного никнейма.
    Если никнейма нет, возвращает стандартное упоминание.
    """
    custom_nick = get_nickname(user.id)
    if custom_nick:
        return f'<a href="tg://user?id={user.id}">{custom_nick}</a>'
    return user.mention_html()

def get_mention_by_id(user_id, default_name="пользователь"):
    """
    Возвращает HTML-упоминание по ID с учетом приоритетов:
    1. Кастомный никнейм (из БД)
    2. Юзернейм (@username) из кэша
    3. Имя (full_name) из кэша
    4. Имя по умолчанию ("пользователь")
    """
    custom_nick = get_nickname(user_id)
    if custom_nick:
        return f'<a href="tg://user?id={user_id}">{custom_nick}</a>'
    
    # Приоритет юзернейму, если нет ника
    username = get_username_by_id(user_id)
    if username:
        return f'<a href="tg://user?id={user_id}">@{username}</a>'
        
    # Если нет юзернейма, берем имя
    full_name = get_full_name_by_id(user_id)
    if full_name:
        return f'<a href="tg://user?id={user_id}">{full_name}</a>'
        
    # Если совсем ничего нет, возвращаем "пользователь"
    return f'<a href="tg://user?id={user_id}">{default_name}</a>'

def update_user_activity(user_id):
    """
    Обновляет дату последнего сообщения. 
    Использует кэш, чтобы не писать в файл чаще чем раз в 5 минут.
    """
    u_id = str(user_id)
    now_ts = time.time()
    
    # Если обновляли недавно — выходим
    if u_id in _activity_cache and (now_ts - _activity_cache[u_id]) < _CACHE_TTL:
        return

    data = load_data(USER_STATS_PATH)
    now_iso = datetime.now().isoformat()
    
    if u_id not in data:
        data[u_id] = {
            "first_appearance": now_iso,
            "last_message": now_iso,
            "rank": 1
        }
    else:
        data[u_id]["last_message"] = now_iso
    
    save_data(data, USER_STATS_PATH)
    _activity_cache[u_id] = now_ts

def get_user_stats(user_id):
    """
    Возвращает статистику пользователя.
    """
    data = load_data(USER_STATS_PATH)
    return data.get(str(user_id), {
        "first_appearance": datetime.now().isoformat(),
        "last_message": datetime.now().isoformat(),
        "rank": 1
    })
