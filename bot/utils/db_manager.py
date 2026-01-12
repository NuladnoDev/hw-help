import asyncio
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from aiogram import types
from supabase import create_client, Client
from bot.config_reader import config
import httpx

# Инициализация клиента Supabase
supabase: Client = create_client(
    config.supabase_url,
    config.supabase_key.get_secret_value()
)

async def _retry_supabase_call(query_builder, retries: int = 3, base_delay: float = 0.5):
    """
    Вспомогательная функция для повторных попыток запроса к Supabase при сетевых ошибках.
    Логические ошибки (неправильный запрос, 4xx и т.п.) не ретраятся, чтобы не подвешивать бота.
    """
    last_exception = None
    delay = base_delay
    for attempt in range(1, retries + 1):
        start = time.monotonic()
        try:
            result = await asyncio.to_thread(query_builder.execute)
            elapsed_ms = (time.monotonic() - start) * 1000
            if elapsed_ms > 800:
                logging.warning(f"Медленный запрос к Supabase ({elapsed_ms:.0f} мс): {query_builder}")
            return result
        except httpx.HTTPError as e:
            last_exception = e
            if attempt < retries:
                logging.warning(
                    f"Сетевая ошибка Supabase (попытка {attempt}/{retries}): {e}. "
                    f"Повтор через {delay:.1f} с..."
                )
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logging.error(f"Supabase недоступен после {retries} попыток: {e}")
        except Exception as e:
            logging.error(f"Ошибка Supabase без ретрая: {e}")
            raise

    raise last_exception

# Кэш для активности
_activity_cache = {}
_CACHE_TTL = 300

# --- Users ---

async def get_user_profile_data(user_id: int, chat_id: int) -> Dict[str, Any]:
    """
    Оптимизированное получение всех данных профиля за минимальное количество запросов.
    """
    # 1. Получаем основные данные пользователя из таблицы users
    # 2. Получаем ранг из chat_members
    # 3. Получаем брак
    # 4. Проверяем наличие наград (счетчик)
    
    # Запускаем параллельно основные запросы с ретраями
    tasks = [
        _retry_supabase_call(supabase.table("users").select("*").eq("user_id", user_id)),
        _retry_supabase_call(supabase.table("chat_members").select("rank").eq("chat_id", chat_id).eq("user_id", user_id)),
        _retry_supabase_call(supabase.table("marriages").select("*").or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}")),
        _retry_supabase_call(supabase.table("awards").select("id", count="exact").eq("chat_id", chat_id).eq("user_id", user_id))
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    data = {
        "nickname": None,
        "description": None,
        "city": None,
        "quote": None,
        "first_appearance": datetime.now(timezone.utc).isoformat(),
        "last_message": datetime.now(timezone.utc).isoformat(),
        "rank_level": 1,
        "marriage": None,
        "has_awards": False
    }
    
    # Обработка users
    if not isinstance(results[0], Exception) and results[0].data:
        u_data = results[0].data[0]
        data.update({
            "nickname": u_data.get("nickname"),
            "description": u_data.get("description"),
            "city": u_data.get("city"),
            "quote": u_data.get("quote"),
            "first_appearance": u_data.get("first_appearance"),
            "last_message": u_data.get("last_message")
        })
        
    # Обработка rank
    if not isinstance(results[1], Exception) and results[1].data:
        data["rank_level"] = results[1].data[0].get("rank", 1)
        
    # Специальная проверка для создателя из конфига
    if config.creator_id and user_id == config.creator_id:
        data["rank_level"] = 5
        
    # Обработка marriage
    if not isinstance(results[2], Exception) and results[2].data:
        m = results[2].data[0]
        data["marriage"] = {
            "partners": [m["user1_id"], m["user2_id"]],
            "created_at": m["created_at"]
        }
        
    # Обработка awards
    if not isinstance(results[3], Exception) and results[3].data:
        data["has_awards"] = len(results[3].data) > 0
        
    return data

async def update_user_cache(user_id: int, username: Optional[str], full_name: Optional[str] = None):
    data = {"user_id": user_id}
    if username:
        data["username"] = username.replace("@", "").lower()
    if full_name:
        data["full_name"] = full_name
    
    try:
        await _retry_supabase_call(supabase.table("users").upsert(data))
    except Exception:
        # Для кэша это не критично, можно просто залогировать
        pass

async def get_username_by_id(user_id: int) -> Optional[str]:
    try:
        res = await _retry_supabase_call(supabase.table("users").select("username").eq("user_id", user_id))
        if res.data:
            return res.data[0].get("username")
    except Exception:
        pass
    return None

async def get_chat_user_ids(chat_id: int) -> List[int]:
    """Возвращает список ID всех пользователей, которые писали в этом чате."""
    try:
        res = await _retry_supabase_call(
            supabase.table("chat_members").select("user_id").eq("chat_id", chat_id)
        )
        return [item["user_id"] for item in res.data] if res.data else []
    except Exception as e:
        logging.error(f"Ошибка при получении участников чата: {e}")
        return []

async def get_full_name_by_id(user_id: int) -> Optional[str]:
    try:
        res = await _retry_supabase_call(supabase.table("users").select("full_name").eq("user_id", user_id))
        if res.data:
            return res.data[0].get("full_name")
    except Exception:
        pass
    return None

async def get_user_id_by_username(username: str) -> Optional[int]:
    clean_username = username.replace("@", "").lower()
    try:
        res = await _retry_supabase_call(supabase.table("users").select("user_id").eq("username", clean_username))
        if res.data:
            return res.data[0].get("user_id")
    except Exception:
        pass
    return None

# --- Mutes & Bans ---

async def add_mute(chat_id: int, user_id: int, until_date: Optional[datetime] = None):
    until = until_date.isoformat() if until_date else None
    try:
        await _retry_supabase_call(supabase.table("mutes").upsert({
            "chat_id": chat_id,
            "user_id": user_id,
            "until": until
        }))
    except Exception as e:
        logging.error(f"Ошибка при добавлении мута: {e}")

async def remove_mute(chat_id: int, user_id: int):
    try:
        await _retry_supabase_call(supabase.table("mutes").delete().eq("chat_id", chat_id).eq("user_id", user_id))
    except Exception as e:
        logging.error(f"Ошибка при удалении мута: {e}")

async def is_user_muted(chat_id: int, user_id: int) -> bool:
    try:
        res = await _retry_supabase_call(supabase.table("mutes").select("*").eq("chat_id", chat_id).eq("user_id", user_id))
        if not res.data:
            return False
        
        until = res.data[0].get("until")
        if not until: # Permanent
            return True
        
        until_date = datetime.fromisoformat(until)
        if until_date > datetime.now(timezone.utc):
            return True
        
        await remove_mute(chat_id, user_id)
    except Exception:
        pass
    return False

async def add_ban(chat_id: int, user_id: int, until_date: Optional[datetime] = None):
    until = until_date.isoformat() if until_date else None
    try:
        await _retry_supabase_call(supabase.table("bans").upsert({
            "chat_id": chat_id,
            "user_id": user_id,
            "until": until
        }))
    except Exception as e:
        logging.error(f"Ошибка при добавлении бана: {e}")

async def remove_ban(chat_id: int, user_id: int):
    try:
        await _retry_supabase_call(supabase.table("bans").delete().eq("chat_id", chat_id).eq("user_id", user_id))
    except Exception as e:
        logging.error(f"Ошибка при удалении бана: {e}")

async def is_user_banned(chat_id: int, user_id: int) -> bool:
    try:
        res = await _retry_supabase_call(supabase.table("bans").select("*").eq("chat_id", chat_id).eq("user_id", user_id))
        if not res.data:
            return False
        
        until = res.data[0].get("until")
        if not until: # Permanent
            return True
        
        until_date = datetime.fromisoformat(until)
        if until_date > datetime.now(timezone.utc):
            return True
        
        await remove_ban(chat_id, user_id)
    except Exception:
        pass
    return False

# --- Warns ---

async def add_warn(chat_id: int, user_id: int, reason: str = "Не указана", until_date: Optional[datetime] = None):
    until = until_date.isoformat() if until_date else None
    try:
        await _retry_supabase_call(supabase.table("warns").insert({
            "chat_id": chat_id,
            "user_id": user_id,
            "reason": reason,
            "until": until
        }))
        
        res = await _retry_supabase_call(supabase.table("warns").select("id", count="exact").eq("chat_id", chat_id).eq("user_id", user_id))
        return len(res.data) if res.data else 0
    except Exception as e:
        logging.error(f"Ошибка при добавлении варна: {e}")
        return 0

async def get_warns(chat_id: int, user_id: int) -> List[Dict]:
    try:
        res = await _retry_supabase_call(supabase.table("warns").select("*").eq("chat_id", chat_id).eq("user_id", user_id))
        if not res.data:
            return []
        
        active_warns = []
        current_time = datetime.now(timezone.utc)
        expired_ids = []
        
        for warn in res.data:
            if not warn["until"]:
                active_warns.append(warn)
            else:
                until_date = datetime.fromisoformat(warn["until"])
                if until_date > current_time:
                    active_warns.append(warn)
                else:
                    expired_ids.append(warn["id"])
        
        if expired_ids:
            await _retry_supabase_call(supabase.table("warns").delete().in_("id", expired_ids))
            
        return active_warns
    except Exception as e:
        logging.error(f"Ошибка при получении варнов: {e}")
        return []

async def remove_last_warn(chat_id: int, user_id: int) -> bool:
    try:
        res = await _retry_supabase_call(supabase.table("warns").select("id").eq("chat_id", chat_id).eq("user_id", user_id).order("id", desc=True).limit(1))
        if res.data:
            await _retry_supabase_call(supabase.table("warns").delete().eq("id", res.data[0]["id"]))
            return True
    except Exception:
        pass
    return False

async def remove_warn_by_index(chat_id: int, user_id: int, index: int) -> bool:
    warns = await get_warns(chat_id, user_id)
    if 0 <= index < len(warns):
        try:
            await _retry_supabase_call(supabase.table("warns").delete().eq("id", warns[index]["id"]))
            return True
        except Exception:
            pass
    return False

async def clear_warns(chat_id: int, user_id: int) -> bool:
    try:
        await _retry_supabase_call(supabase.table("warns").delete().eq("chat_id", chat_id).eq("user_id", user_id))
        return True
    except Exception:
        return False

# --- Nicknames & Descriptions ---

async def set_nickname(user_id: int, nickname: str):
    try:
        await _retry_supabase_call(supabase.table("users").upsert({"user_id": user_id, "nickname": nickname}))
    except Exception as e:
        logging.error(f"Ошибка при установке никнейма: {e}")

async def remove_nickname(user_id: int) -> bool:
    try:
        await _retry_supabase_call(supabase.table("users").update({"nickname": None}).eq("user_id", user_id))
        return True
    except Exception:
        return False

async def get_nickname(user_id: int) -> Optional[str]:
    try:
        res = await _retry_supabase_call(supabase.table("users").select("nickname").eq("user_id", user_id))
        if res.data:
            return res.data[0].get("nickname")
    except Exception:
        pass
    return None

async def set_description(user_id: int, description: str):
    try:
        await _retry_supabase_call(supabase.table("users").upsert({"user_id": user_id, "description": description}))
    except Exception as e:
        logging.error(f"Ошибка при установке описания: {e}")

async def remove_description(user_id: int) -> bool:
    try:
        await _retry_supabase_call(supabase.table("users").update({"description": None}).eq("user_id", user_id))
        return True
    except Exception:
        return False

async def get_description(user_id: int) -> Optional[str]:
    try:
        res = await _retry_supabase_call(supabase.table("users").select("description").eq("user_id", user_id))
        if res.data:
            return res.data[0].get("description")
    except Exception:
        pass
    return None

# --- City ---

async def set_city(user_id: int, city: str):
    try:
        await _retry_supabase_call(supabase.table("users").upsert({"user_id": user_id, "city": city}))
    except Exception as e:
        logging.error(f"Ошибка при установке города: {e}")

async def remove_city(user_id: int) -> bool:
    try:
        await _retry_supabase_call(supabase.table("users").update({"city": None}).eq("user_id", user_id))
        return True
    except Exception:
        return False

async def get_city(user_id: int) -> Optional[str]:
    try:
        res = await _retry_supabase_call(supabase.table("users").select("city").eq("user_id", user_id))
        if res.data:
            return res.data[0].get("city")
    except Exception:
        pass
    return None

# --- Quote ---

async def set_quote(user_id: int, quote: str):
    try:
        await _retry_supabase_call(supabase.table("users").upsert({"user_id": user_id, "quote": quote}))
    except Exception as e:
        logging.error(f"Ошибка при установке цитаты: {e}")

async def remove_quote(user_id: int) -> bool:
    try:
        await _retry_supabase_call(supabase.table("users").update({"quote": None}).eq("user_id", user_id))
        return True
    except Exception:
        return False

async def get_quote(user_id: int) -> Optional[str]:
    try:
        res = await _retry_supabase_call(supabase.table("users").select("quote").eq("user_id", user_id))
        if res.data:
            return res.data[0].get("quote")
    except Exception:
        pass
    return None

# --- Awards ---

async def add_award(chat_id: int, target_user_id: int, admin_user_id: int, text: str) -> int:
    try:
        await _retry_supabase_call(supabase.table("awards").insert({
            "chat_id": chat_id,
            "user_id": target_user_id,
            "from_id": admin_user_id,
            "text": text
        }))
        
        res = await _retry_supabase_call(supabase.table("awards").select("id", count="exact").eq("chat_id", chat_id).eq("user_id", target_user_id))
        return len(res.data) if res.data else 0
    except Exception as e:
        logging.error(f"Ошибка при добавлении награды: {e}")
        return 0

async def get_awards(chat_id: int, user_id: int) -> List[Dict]:
    try:
        res = await _retry_supabase_call(supabase.table("awards").select("*").eq("chat_id", chat_id).eq("user_id", user_id))
        return res.data or []
    except Exception:
        return []

async def remove_award_by_index(chat_id: int, user_id: int, index: int) -> bool:
    awards = await get_awards(chat_id, user_id)
    if 0 <= index < len(awards):
        try:
            await _retry_supabase_call(supabase.table("awards").delete().eq("id", awards[index]["id"]))
            return True
        except Exception:
            pass
    return False

# --- Ranks ---

RANKS = {
    0: "Обычный пользователь",
    1: "Помощник модератора",
    2: "Младший модератор",
    3: "Модератор",
    4: "Администратор",
    5: "Создатель"
}

# Падежи по умолчанию
DEFAULT_RANK_CASES = {
    0: {"nom": "Обычный пользователь", "gen": "Обычного пользователя", "ins": "Обычным пользователем"},
    1: {"nom": "Помощник модератора", "gen": "Помощника модератора", "ins": "Помощником модератора"},
    2: {"nom": "Младший модератор", "gen": "Младшего модератора", "ins": "Младшим модератором"},
    3: {"nom": "Модератор", "gen": "Модератора", "ins": "Модератором"},
    4: {"nom": "Администратор", "gen": "Администратора", "ins": "Администратором"},
    5: {"nom": "Создатель", "gen": "Создателя", "ins": "Создателем"}
}

async def get_group_rank_name(chat_id: int, rank_level: int, case: str = "nom") -> str:
    """Получает название ранга для конкретной группы с учетом падежа."""
    try:
        res = await _retry_supabase_call(
            supabase.table("group_ranks")
            .select(f"name_{case}")
            .eq("chat_id", chat_id)
            .eq("rank_number", rank_level)
        )
        
        if res.data:
            rank_name = res.data[0].get(f"name_{case}")
            logging.info(f"DEBUG: Получено кастомное название ранга для чата {chat_id}, уровень {rank_level}: {rank_name}")
            return rank_name
        else:
            logging.info(f"DEBUG: Кастомное название ранга для чата {chat_id}, уровень {rank_level} не найдено, используем дефолт.")
    except Exception as e:
        logging.warning(f"Ошибка при получении названия ранга из БД (чат {chat_id}, уровень {rank_level}): {e}")
    
    # Возвращаем дефолтное значение
    return DEFAULT_RANK_CASES.get(rank_level, {}).get(case, RANKS.get(rank_level, "Неизвестно"))

async def set_group_rank_names(chat_id: int, rank_level: int, nom: str, gen: str, ins: str):
    """Устанавливает кастомные названия для ранга в группе."""
    try:
        await _retry_supabase_call(
            supabase.table("group_ranks").upsert({
                "chat_id": chat_id,
                "rank_number": rank_level,
                "name_nom": nom,
                "name_gen": gen,
                "name_ins": ins
            })
        )
    except Exception as e:
        logging.error(f"Ошибка при сохранении названий рангов: {e}")

async def get_rank(user_id: int, chat_id: int) -> Tuple[int, str]:
    if config.creator_id and user_id == config.creator_id:
        name = await get_group_rank_name(chat_id, 5, "nom")
        return 5, name
    
    try:
        res = await _retry_supabase_call(
            supabase.table("chat_members").select("rank").eq("chat_id", chat_id).eq("user_id", user_id)
        )
        if res.data:
            rank_level = res.data[0].get("rank", 0)
            name = await get_group_rank_name(chat_id, rank_level, "nom")
            return rank_level, name
    except Exception as e:
        logging.error(f"Ошибка при получении ранга пользователя {user_id}: {e}")
    
    name = await get_group_rank_name(chat_id, 0, "nom")
    return 0, name

async def set_rank(user_id: int, chat_id: int, rank_level: int) -> bool:
    if rank_level not in RANKS or rank_level < 1:
        return False
    try:
        await _retry_supabase_call(
            supabase.table("chat_members").upsert({
                "chat_id": chat_id,
                "user_id": user_id,
                "rank": rank_level
            })
        )
        return True
    except Exception as e:
        logging.error(f"Ошибка при сохранении ранга пользователя {user_id}: {e}")
        return False

async def get_user_rank_context(user_id: int, chat: types.Chat) -> Tuple[int, str, bool]:
    if config.creator_id and user_id == config.creator_id:
        name = await get_group_rank_name(chat.id, 5, "nom")
        return 5, name, True
        
    try:
        member = await chat.get_member(user_id)
        if member.status == "creator":
            name = await get_group_rank_name(chat.id, 5, "nom")
            return 5, name, True
        
        # Если администратор Telegram, даем минимум 4 ранг
        is_tg_admin = member.status == "administrator"
    except Exception:
        is_tg_admin = False
    
    level, name = await get_rank(user_id, chat.id)
    
    if is_tg_admin and level < 4:
        level = 4
        name = await get_group_rank_name(chat.id, 4, "nom")
        
    return level, name, False

async def can_user_modify_other(admin_user_id: int, target_user_id: int, chat: types.Chat) -> bool:
    if admin_user_id == target_user_id:
        return True
    admin_rank, _, is_admin_super = await get_user_rank_context(admin_user_id, chat)
    target_rank, _, is_target_super = await get_user_rank_context(target_user_id, chat)
    if is_admin_super:
        return not is_target_super
    return admin_rank > target_rank

async def get_all_ranked_users(chat_id: int) -> Dict[int, int]:
    try:
        res = await _retry_supabase_call(supabase.table("chat_members").select("user_id", "rank").eq("chat_id", chat_id))
        return {item["user_id"]: item["rank"] for item in res.data} if res.data else {}
    except Exception as e:
        logging.error(f"Ошибка при получении всех ранжированных пользователей: {e}")
        return {}

# --- Invites ---

async def save_inviter(chat_id: int, user_id: int, inviter_id: int):
    try:
        await _retry_supabase_call(supabase.table("inviters").upsert({
            "chat_id": chat_id,
            "user_id": user_id,
            "inviter_id": inviter_id
        }))
    except Exception as e:
        logging.error(f"Ошибка при сохранении пригласившего: {e}")

async def get_inviter(chat_id: int, user_id: int) -> Optional[int]:
    try:
        res = await _retry_supabase_call(supabase.table("inviters").select("inviter_id").eq("chat_id", chat_id).eq("user_id", user_id))
        if res.data:
            return res.data[0].get("inviter_id")
    except Exception:
        pass
    return None

# --- Marriages ---

async def create_marriage(user1_id: int, user2_id: int):
    u1, u2 = sorted([user1_id, user2_id])
    try:
        await _retry_supabase_call(supabase.table("marriages").upsert({
            "user1_id": u1,
            "user2_id": u2
        }))
    except Exception as e:
        logging.error(f"Ошибка при создании брака: {e}")

async def get_marriage(user_id: int) -> Optional[Dict]:
    try:
        res = await _retry_supabase_call(supabase.table("marriages").select("*").or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}"))
        if res.data:
            m = res.data[0]
            return {
                "partners": [m["user1_id"], m["user2_id"]],
                "created_at": m["created_at"]
            }
    except Exception:
        pass
    return None

async def remove_marriage(user_id: int) -> bool:
    try:
        res = await _retry_supabase_call(supabase.table("marriages").delete().or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}"))
        return True if res.data else False
    except Exception:
        return False

# --- Relationships ---

async def update_relationship(user1_id: int, user2_id: int, action_type: str) -> Dict:
    u1, u2 = sorted([int(user1_id), int(user2_id)])
    
    try:
        # Сначала получаем текущие данные
        res = await _retry_supabase_call(supabase.table("relationships").select("*").eq("user1_id", u1).eq("user2_id", u2))
        
        if res.data:
            rel = res.data[0]
            actions = rel.get("actions", {})
            actions[action_type] = actions.get(action_type, 0) + 1
            total = rel.get("total_interactions", 0) + 1
        else:
            actions = {action_type: 1}
            total = 1
        
        # Обновляем или вставляем
        data = {
            "user1_id": u1,
            "user2_id": u2,
            "actions": actions,
            "total_interactions": total,
            "last_interaction": datetime.now(timezone.utc).isoformat()
        }
        
        res = await _retry_supabase_call(supabase.table("relationships").upsert(data))
        return res.data[0] if res.data else {}
    except Exception as e:
        logging.error(f"Ошибка при обновлении отношений: {e}")
        return {}

async def get_relationship(user1_id: int, user2_id: int) -> Optional[Dict]:
    u1, u2 = sorted([int(user1_id), int(user2_id)])
    try:
        res = await _retry_supabase_call(supabase.table("relationships").select("*").eq("user1_id", u1).eq("user2_id", u2))
        return res.data[0] if res.data else None
    except Exception:
        return None

async def delete_relationship(user1_id: int, user2_id: int) -> bool:
    u1, u2 = sorted([int(user1_id), int(user2_id)])
    try:
        await _retry_supabase_call(supabase.table("relationships").delete().eq("user1_id", u1).eq("user2_id", u2))
        return True
    except Exception:
        return False

async def get_all_user_relationships(user_id: int) -> List[Dict]:
    try:
        res = await _retry_supabase_call(supabase.table("relationships").select("*").or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}"))
        if not res.data:
            return []
        
        results = []
        for rel in res.data:
            partner_id = rel["user2_id"] if rel["user1_id"] == user_id else rel["user1_id"]
            results.append({
                "partner_id": partner_id,
                "data": rel
            })
        
        results.sort(key=lambda x: x["data"]["total_interactions"], reverse=True)
        return results
    except Exception:
        return []

# --- Mentions ---

async def get_user_mention_with_nickname(user: types.User) -> str:
    custom_nick = await get_nickname(user.id)
    if custom_nick:
        return f'<a href="tg://user?id={user.id}">{custom_nick}</a>'
    return user.mention_html()

async def get_mention_by_id(user_id: int, default_name: str = "пользователь") -> str:
    custom_nick = await get_nickname(user_id)
    if custom_nick:
        return f'<a href="tg://user?id={user_id}">{custom_nick}</a>'
    
    username = await get_username_by_id(user_id)
    if username:
        return f'<a href="tg://user?id={user_id}">@{username}</a>'
        
    full_name = await get_full_name_by_id(user_id)
    if full_name:
        return f'<a href="tg://user?id={user_id}">{full_name}</a>'
        
    return f'<a href="tg://user?id={user_id}">{default_name}</a>'

# --- Stats ---

async def update_user_activity(user_id: int):
    now_ts = time.time()
    if user_id in _activity_cache and (now_ts - _activity_cache[user_id]) < _CACHE_TTL:
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        await _retry_supabase_call(supabase.table("users").upsert({
            "user_id": user_id,
            "last_message": now_iso
        }))
        
        today = datetime.now(timezone.utc).date().isoformat()
        res = await _retry_supabase_call(
            supabase.table("activity_stats")
            .select("count")
            .eq("user_id", user_id)
            .eq("date", today)
        )
        if res.data:
            current = res.data[0].get("count", 0) or 0
            await _retry_supabase_call(
                supabase.table("activity_stats")
                .update({"count": current + 1})
                .eq("user_id", user_id)
                .eq("date", today)
            )
        else:
            await _retry_supabase_call(
                supabase.table("activity_stats")
                .insert({"user_id": user_id, "date": today, "count": 1})
            )
        
        _activity_cache[user_id] = now_ts
    except Exception as e:
        logging.warning(f"Ошибка при обновлении активности (RLS/DB): {e}")

async def get_user_stats(user_id: int) -> Dict:
    try:
        res = await _retry_supabase_call(supabase.table("users").select("first_appearance", "last_message").eq("user_id", user_id))
        if res.data:
            return res.data[0]
    except Exception:
        pass
    return {
        "first_appearance": datetime.now(timezone.utc).isoformat(),
        "last_message": datetime.now(timezone.utc).isoformat()
    }

async def get_user_activity_series(user_id: int, days: int = 30) -> List[Tuple[datetime, int]]:
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)
    
    try:
        res = await _retry_supabase_call(
            supabase.table("activity_stats")
            .select("date,count")
            .eq("user_id", user_id)
            .gte("date", start_date.isoformat())
            .order("date")
        )
        
        raw = {datetime.fromisoformat(item["date"]).date(): item.get("count", 0) for item in (res.data or [])}
    except Exception:
        raw = {}
    
    series: List[Tuple[datetime, int]] = []
    current = start_date
    while current <= today:
        series.append((current, raw.get(current, 0)))
        current += timedelta(days=1)
    
    return series

async def get_user_activity_summary(user_id: int) -> Dict[str, int]:
    """Возвращает статистику сообщений за день, неделю, месяц и все время."""
    # Получаем серию за 30 дней для расчета д|н|м
    series_30 = await get_user_activity_series(user_id, days=30)
    
    summary = {"day": 0, "week": 0, "month": 0, "total": 0}
    
    if series_30:
        # День (сегодня)
        summary["day"] = series_30[-1][1]
        # Неделя (последние 7 дней)
        summary["week"] = sum(count for _, count in series_30[-7:])
        # Месяц (все 30 дней)
        summary["month"] = sum(count for _, count in series_30)
        
    # Для "все время" суммируем все записи из таблицы
    try:
        res = await _retry_supabase_call(
            supabase.table("activity_stats")
            .select("count")
            .eq("user_id", user_id)
        )
        if res.data:
            summary["total"] = sum(item.get("count", 0) or 0 for item in res.data)
    except Exception:
        pass
            
    return summary

# --- Group Settings ---

async def set_welcome_message(chat_id: int, message_text: str):
    """Сохраняет текст приветствия для группы."""
    try:
        await _retry_supabase_call(
            supabase.table("group_settings").upsert({
                "chat_id": chat_id,
                "welcome_message": message_text
            })
        )
    except Exception as e:
        logging.error(f"Ошибка при сохранении приветствия: {e}")

async def get_welcome_message(chat_id: int) -> Optional[str]:
    """Получает текст приветствия для группы."""
    try:
        res = await _retry_supabase_call(
            supabase.table("group_settings").select("welcome_message").eq("chat_id", chat_id)
        )
        if res.data:
            return res.data[0].get("welcome_message")
    except Exception as e:
        logging.error(f"Ошибка при получении приветствия: {e}")
    return None

async def get_disabled_modules(chat_id: int) -> List[str]:
    """Возвращает список идентификаторов выключенных модулей для чата."""
    try:
        res = await _retry_supabase_call(
            supabase.table("group_settings").select("disabled_modules").eq("chat_id", chat_id)
        )
        if res.data and res.data[0].get("disabled_modules"):
            return res.data[0]["disabled_modules"]
    except Exception as e:
        logging.error(f"Ошибка при получении списка модулей: {e}")
    return []

async def toggle_module(chat_id: int, module_id: str, enable: bool):
    """Включает или выключает модуль в группе."""
    current_disabled = await get_disabled_modules(chat_id)
    
    if enable:
        if module_id in current_disabled:
            current_disabled.remove(module_id)
    else:
        if module_id not in current_disabled:
            current_disabled.append(module_id)
            
    try:
        await _retry_supabase_call(
            supabase.table("group_settings").upsert({
                "chat_id": chat_id,
                "disabled_modules": current_disabled
            })
        )
    except Exception as e:
        logging.error(f"Ошибка при сохранении настроек модулей: {e}")

async def get_permission_settings(chat_id: int) -> Dict[str, int]:
    """Возвращает настройки минимальных рангов для действий в группе."""
    try:
        res = await _retry_supabase_call(
            supabase.table("group_settings").select("permission_settings").eq("chat_id", chat_id)
        )
        if res.data and res.data[0].get("permission_settings"):
            return res.data[0]["permission_settings"]
    except Exception as e:
        logging.error(f"Ошибка при получении настроек прав: {e}")
    return {}

async def set_permission_rank(chat_id: int, action_id: str, min_rank: int):
    """Устанавливает минимальный ранг для конкретного действия."""
    current_settings = await get_permission_settings(chat_id)
    current_settings[action_id] = min_rank
    
    try:
        await _retry_supabase_call(
            supabase.table("group_settings").upsert({
                "chat_id": chat_id,
                "permission_settings": current_settings
            })
        )
    except Exception as e:
        logging.error(f"Ошибка при сохранении настроек прав: {e}")

# --- Clans ---

async def create_clan(chat_id: int, name: str, creator_id: int) -> Optional[int]:
    """Создает новый клан и возвращает его ID."""
    try:
        res = await _retry_supabase_call(
            supabase.table("clans").insert({
                "chat_id": chat_id,
                "name": name,
                "creator_id": creator_id
            })
        )
        if res.data:
            clan_id = res.data[0]["id"]
            # Сразу добавляем создателя в клан
            await join_clan(chat_id, clan_id, creator_id)
            return clan_id
    except Exception as e:
        logging.error(f"Ошибка при создании клана: {e}")
    return None

async def get_clan_by_name(chat_id: int, name: str) -> Optional[Dict]:
    """Получает информацию о клане по названию в чате."""
    try:
        res = await _retry_supabase_call(
            supabase.table("clans").select("*").eq("chat_id", chat_id).ilike("name", name)
        )
        return res.data[0] if res.data else None
    except Exception:
        return None

async def get_clan_by_id(clan_id: int) -> Optional[Dict]:
    """Получает информацию о клане по ID."""
    try:
        res = await _retry_supabase_call(
            supabase.table("clans").select("*").eq("id", clan_id)
        )
        return res.data[0] if res.data else None
    except Exception:
        return None

async def delete_clan(clan_id: int):
    """Удаляет клан."""
    try:
        await _retry_supabase_call(
            supabase.table("clans").delete().eq("id", clan_id)
        )
    except Exception as e:
        logging.error(f"Ошибка при удалении клана: {e}")

async def join_clan(chat_id: int, clan_id: int, user_id: int) -> bool:
    """Добавляет пользователя в клан (выходя из предыдущего)."""
    try:
        # В клане можно быть только в одном (PRIMARY KEY на chat_id, user_id)
        await _retry_supabase_call(
            supabase.table("clan_members").upsert({
                "chat_id": chat_id,
                "clan_id": clan_id,
                "user_id": user_id
            })
        )
        return True
    except Exception as e:
        logging.error(f"Ошибка при вступлении в клан: {e}")
        return False

async def leave_clan(chat_id: int, user_id: int):
    """Удаляет пользователя из клана."""
    try:
        await _retry_supabase_call(
            supabase.table("clan_members").delete().eq("chat_id", chat_id).eq("user_id", user_id)
        )
    except Exception as e:
        logging.error(f"Ошибка при выходе из клана: {e}")

async def get_user_clan(chat_id: int, user_id: int) -> Optional[Dict]:
    """Возвращает информацию о клане, в котором состоит пользователь."""
    try:
        res = await _retry_supabase_call(
            supabase.table("clan_members").select("clan_id, clans(*)").eq("chat_id", chat_id).eq("user_id", user_id)
        )
        if res.data and res.data[0].get("clans"):
            return res.data[0]["clans"]
    except Exception:
        pass
    return None

async def get_clan_members(clan_id: int) -> List[int]:
    """Возвращает список ID пользователей в клане."""
    try:
        res = await _retry_supabase_call(
            supabase.table("clan_members").select("user_id").eq("clan_id", clan_id)
        )
        return [item["user_id"] for item in res.data] if res.data else []
    except Exception:
        return []

async def get_all_clans(chat_id: int) -> List[Dict]:
    """Возвращает список всех кланов в чате."""
    try:
        res = await _retry_supabase_call(
            supabase.table("clans").select("*").eq("chat_id", chat_id).order("created_at")
        )
        return res.data if res.data else []
    except Exception as e:
        logging.error(f"Ошибка при получении списка кланов: {e}")
        return []

# --- Clubs ---

async def create_club(chat_id: int, name: str, creator_id: int) -> Optional[int]:
    """Создает новый кружок."""
    try:
        res = await _retry_supabase_call(
            supabase.table("clubs").insert({
                "chat_id": chat_id,
                "name": name,
                "creator_id": creator_id
            })
        )
        if res.data:
            club_id = res.data[0]["id"]
            await join_club(chat_id, club_id, creator_id)
            return club_id
    except Exception as e:
        logging.error(f"Ошибка при создании кружка: {e}")
    return None

async def get_club_by_name(chat_id: int, name: str) -> Optional[Dict]:
    """Получает информацию о кружке по названию."""
    try:
        res = await _retry_supabase_call(
            supabase.table("clubs").select("*").eq("chat_id", chat_id).ilike("name", name)
        )
        return res.data[0] if res.data else None
    except Exception:
        return None

async def delete_club(club_id: int):
    """Удаляет кружок."""
    try:
        await _retry_supabase_call(
            supabase.table("clubs").delete().eq("id", club_id)
        )
    except Exception as e:
        logging.error(f"Ошибка при удалении кружка: {e}")

async def join_club(chat_id: int, club_id: int, user_id: int) -> bool:
    """Добавляет пользователя в кружок."""
    try:
        await _retry_supabase_call(
            supabase.table("club_members").upsert({
                "chat_id": chat_id,
                "club_id": club_id,
                "user_id": user_id
            })
        )
        return True
    except Exception as e:
        logging.error(f"Ошибка при вступлении в кружок: {e}")
        return False

async def leave_club(chat_id: int, club_id: int, user_id: int):
    """Удаляет пользователя из кружка."""
    try:
        await _retry_supabase_call(
            supabase.table("club_members").delete().eq("chat_id", chat_id).eq("club_id", club_id).eq("user_id", user_id)
        )
    except Exception as e:
        logging.error(f"Ошибка при выходе из кружка: {e}")

async def get_user_clubs(chat_id: int, user_id: int) -> List[Dict]:
    """Возвращает список кружков, в которых состоит пользователь."""
    try:
        res = await _retry_supabase_call(
            supabase.table("club_members").select("club_id, clubs(*)").eq("chat_id", chat_id).eq("user_id", user_id)
        )
        return [item["clubs"] for item in res.data if item.get("clubs")] if res.data else []
    except Exception:
        return []

async def get_club_members(club_id: int) -> List[int]:
    """Возвращает список ID пользователей в кружке."""
    try:
        res = await _retry_supabase_call(
            supabase.table("club_members").select("user_id").eq("club_id", club_id)
        )
        return [item["user_id"] for item in res.data] if res.data else []
    except Exception:
        return []

async def get_all_clubs(chat_id: int) -> List[Dict]:
    """Возвращает список всех кружков в чате."""
    try:
        res = await _retry_supabase_call(
            supabase.table("clubs").select("*").eq("chat_id", chat_id).order("created_at")
        )
        return res.data if res.data else []
    except Exception as e:
        logging.error(f"Ошибка при получении списка кружков: {e}")
        return []

# --- Репутация ---

async def update_reputation(chat_id: int, user_id: int, delta: int) -> Dict[str, int]:
    """Изменяет репутацию пользователя и возвращает словарь со статистикой."""
    try:
        # Сначала получаем текущее значение
        res = await _retry_supabase_call(
            supabase.table("reputation").select("*").eq("chat_id", chat_id).eq("user_id", user_id)
        )
        
        data = res.data[0] if res.data else {"points": 0, "plus_count": 0, "minus_count": 0}
        
        current_points = data.get("points", 0)
        current_plus = data.get("plus_count", 0)
        current_minus = data.get("minus_count", 0)
        
        new_points = current_points + delta
        new_plus = current_plus + (1 if delta > 0 else 0)
        new_minus = current_minus + (1 if delta < 0 else 0)
        
        stats = {
            "chat_id": chat_id,
            "user_id": user_id,
            "points": new_points,
            "plus_count": new_plus,
            "minus_count": new_minus
        }
        
        await _retry_supabase_call(
            supabase.table("reputation").upsert(stats)
        )
        return stats
    except Exception as e:
        logging.error(f"Ошибка при обновлении репутации: {e}")
        return {"points": 0, "plus_count": 0, "minus_count": 0}

async def get_user_reputation(chat_id: int, user_id: int) -> Dict[str, int]:
    """Возвращает статистику репутации пользователя."""
    try:
        res = await _retry_supabase_call(
            supabase.table("reputation").select("*").eq("chat_id", chat_id).eq("user_id", user_id)
        )
        if res.data:
            return {
                "points": res.data[0].get("points", 0),
                "plus_count": res.data[0].get("plus_count", 0),
                "minus_count": res.data[0].get("minus_count", 0)
            }
    except Exception:
        pass
    return {"points": 0, "plus_count": 0, "minus_count": 0}

async def get_top_reputation(chat_id: int, limit: int = 10) -> List[Dict]:
    """Возвращает топ пользователей по репутации в чате."""
    try:
        # Мы хотим получить поинты и данные пользователя
        res = await _retry_supabase_call(
            supabase.table("reputation")
            .select("points, user_id, users(full_name, nickname)")
            .eq("chat_id", chat_id)
            .order("points", desc=True)
            .limit(limit)
        )
        return res.data if res.data else []
    except Exception as e:
        logging.error(f"Ошибка при получении топа репутации: {e}")
        return []

async def add_antispam_report(reporter_id: int, target_id: int, chat_id: int) -> Dict:
    """
    Добавляет жалобу на пользователя. 
    Ограничение: 1 жалоба в сутки от одного пользователя.
    При достижении 5 жалоб пользователь попадает в черный список.
    """
    try:
        # 1. Проверяем лимит (1 жалоба в 24 часа)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        
        check_res = await _retry_supabase_call(
            supabase.table("antispam_reports")
            .select("id")
            .eq("reporter_id", reporter_id)
            .gt("created_at", yesterday)
            .limit(1)
        )
        
        if check_res.data:
            return {"status": "limit_exceeded"}

        # 2. Добавляем жалобу
        await _retry_supabase_call(
            supabase.table("antispam_reports").insert({
                "reporter_id": reporter_id,
                "target_id": target_id,
                "chat_id": chat_id
            })
        )

        # 3. Считаем общее количество жалоб
        count_res = await _retry_supabase_call(
            supabase.table("antispam_reports")
            .select("id", count="exact")
            .eq("target_id", target_id)
        )
        
        report_count = count_res.count if count_res.count is not None else 0

        # 4. Если жалоб 5 или больше — в черный список
        is_blacklisted = False
        if report_count >= 5:
            # Проверяем, нет ли уже в списке
            bl_check = await _retry_supabase_call(
                supabase.table("antispam_blacklist").select("user_id").eq("user_id", target_id)
            )
            if not bl_check.data:
                await _retry_supabase_call(
                    supabase.table("antispam_blacklist").insert({"user_id": target_id})
                )
                is_blacklisted = True

        return {
            "status": "success",
            "count": report_count,
            "is_blacklisted": is_blacklisted
        }
    except Exception as e:
        logging.error(f"Ошибка при добавлении жалобы антиспам: {e}")
        return {"status": "error"}

# Глобальный кэш для черного списка антиспама
_blacklist_cache = set()
_blacklist_last_update = 0

async def is_user_blacklisted(user_id: int) -> bool:
    """Проверяет, находится ли пользователь в черном списке антиспама."""
    global _blacklist_last_update
    
    # Обновляем кэш раз в 5 минут
    if time.time() - _blacklist_last_update > 300:
        try:
            res = await _retry_supabase_call(
                supabase.table("antispam_blacklist").select("user_id")
            )
            if res.data:
                _blacklist_cache.clear()
                for item in res.data:
                    _blacklist_cache.add(item["user_id"])
                _blacklist_last_update = time.time()
        except Exception as e:
            logging.error(f"Ошибка при проверке черного списка: {e}")
            
    return user_id in _blacklist_cache

async def get_user_balance(user_id: int) -> int:
    """Возвращает текущий баланс койнов пользователя."""
    try:
        res = await _retry_supabase_call(
            supabase.table("economy").select("coins").eq("user_id", user_id).limit(1)
        )
        if res.data:
            return res.data[0]["coins"]
        return 0
    except Exception as e:
        logging.error(f"Ошибка при получении баланса {user_id}: {e}")
        return 0

async def update_user_balance(user_id: int, amount: int) -> int:
    """
    Изменяет баланс пользователя на указанную сумму.
    Использует upsert для создания записи, если её нет.
    """
    try:
        # Сначала получаем текущий баланс
        current = await get_user_balance(user_id)
        new_balance = current + amount
        
        # Обновляем (или вставляем)
        await _retry_supabase_call(
            supabase.table("economy").upsert({
                "user_id": user_id,
                "coins": new_balance
            })
        )
        return new_balance
    except Exception as e:
        logging.error(f"Ошибка при обновлении баланса {user_id}: {e}")
        return 0

async def transfer_coins(from_id: int, to_id: int, amount: int) -> bool:
    """Переводит койны от одного пользователя другому."""
    if amount <= 0:
        return False
        
    try:
        current_from = await get_user_balance(from_id)
        if current_from < amount:
            return False
            
        # Уменьшаем у отправителя
        await update_user_balance(from_id, -amount)
        # Увеличиваем у получателя
        await update_user_balance(to_id, amount)
        return True
    except Exception as e:
        logging.error(f"Ошибка при переводе койнов: {e}")
        return False

# --- Levels ---

def _xp_for_level(level: int) -> int:
    """Сколько опыта нужно для перехода с уровня level на level+1."""
    return 50 + level * 25

def _coins_for_level(level: int) -> int:
    """Сколько койнов выдается за получение указанного уровня."""
    return 100 * level

async def get_user_level(user_id: int) -> Dict[str, int]:
    """
    Возвращает данные по уровню пользователя:
    level, xp, needed_xp, remaining_xp, next_reward_coins.
    """
    level = 0
    xp = 0
    try:
        res = await _retry_supabase_call(
            supabase.table("user_levels").select("*").eq("user_id", user_id).limit(1)
        )
        if res.data:
            row = res.data[0]
            level = int(row.get("level", 0) or 0)
            xp = int(row.get("xp", 0) or 0)
    except Exception as e:
        logging.error(f"Ошибка при получении уровня пользователя {user_id}: {e}")
    
    needed_xp = _xp_for_level(level)
    remaining_xp = max(0, needed_xp - xp)
    next_reward_coins = _coins_for_level(level + 1)
    
    return {
        "level": level,
        "xp": xp,
        "needed_xp": needed_xp,
        "remaining_xp": remaining_xp,
        "next_reward_coins": next_reward_coins
    }

async def add_user_xp(user_id: int, amount: int) -> Dict[str, Any]:
    """
    Добавляет пользователю опыт.
    При достижении новых уровней автоматически начисляет койны.
    Возвращает данные по текущему уровню и список апнутых уровней.
    """
    if amount <= 0:
        data = await get_user_level(user_id)
        data["leveled_up"] = []
        data["total_reward_coins"] = 0
        return data
    
    level = 0
    xp = 0
    try:
        res = await _retry_supabase_call(
            supabase.table("user_levels").select("level,xp").eq("user_id", user_id).limit(1)
        )
        if res.data:
            row = res.data[0]
            level = int(row.get("level", 0) or 0)
            xp = int(row.get("xp", 0) or 0)
    except Exception:
        pass
    
    xp += amount
    leveled_up: List[Dict[str, int]] = []
    total_reward = 0
    
    while xp >= _xp_for_level(level):
        need = _xp_for_level(level)
        if xp < need:
            break
        xp -= need
        level += 1
        reward = _coins_for_level(level)
        total_reward += reward
        await update_user_balance(user_id, reward)
        leveled_up.append({"level": level, "reward": reward})
    
    try:
        await _retry_supabase_call(
            supabase.table("user_levels").upsert({
                "user_id": user_id,
                "level": level,
                "xp": xp,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        )
    except Exception as e:
        logging.error(f"Ошибка при сохранении уровня пользователя {user_id}: {e}")
    
    data = await get_user_level(user_id)
    data["leveled_up"] = leveled_up
    data["total_reward_coins"] = total_reward
    return data

async def apply_once_level_bonus(user_id: int, bonus_type: str, amount: int) -> Dict[str, Any]:
    """
    Одноразовый бонус опыта за событие (брак, клан, кружок).
    bonus_type: 'marriage' | 'clan' | 'club'
    """
    column_map = {
        "marriage": "has_marriage_bonus",
        "clan": "has_clan_bonus",
        "club": "has_club_bonus",
    }
    column = column_map.get(bonus_type)
    if not column:
        return await add_user_xp(user_id, 0)
    
    try:
        res = await _retry_supabase_call(
            supabase.table("user_levels").select(column).eq("user_id", user_id).limit(1)
        )
        if res.data and res.data[0].get(column):
            return await get_user_level(user_id)
        
        if res.data:
            await _retry_supabase_call(
                supabase.table("user_levels").update({column: True, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("user_id", user_id)
            )
        else:
            await _retry_supabase_call(
                supabase.table("user_levels").insert({
                    "user_id": user_id,
                    column: True,
                    "level": 0,
                    "xp": 0,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
            )
    except Exception as e:
        logging.error(f"Ошибка при применении одноразового бонуса {bonus_type} для {user_id}: {e}")
    
    return await add_user_xp(user_id, amount)

# --- Каталог ---

async def get_chat_balance(chat_id: int) -> int:
    """Возвращает баланс чата."""
    try:
        res = await _retry_supabase_call(
            supabase.table("chat_economy").select("coins").eq("chat_id", chat_id).limit(1)
        )
        if res.data:
            return res.data[0]["coins"]
        return 0
    except Exception as e:
        logging.error(f"Ошибка при получении баланса чата {chat_id}: {e}")
        return 0

async def update_chat_balance(chat_id: int, amount: int) -> int:
    """Обновляет баланс чата."""
    try:
        current = await get_chat_balance(chat_id)
        new_balance = max(0, current + amount)
        await _retry_supabase_call(
            supabase.table("chat_economy").upsert({
                "chat_id": chat_id,
                "coins": new_balance
            })
        )
        return new_balance
    except Exception as e:
        logging.error(f"Ошибка при обновлении баланса чата {chat_id}: {e}")
        return 0

async def get_catalog_categories() -> List[dict]:
    """Возвращает список категорий каталога."""
    try:
        res = await _retry_supabase_call(
            supabase.table("catalog_categories").select("*")
        )
        return res.data or []
    except Exception as e:
        logging.error(f"Ошибка при получении категорий каталога: {e}")
        return []

async def add_catalog_request(chat_id: int, category_id: int, added_by: int, link: str = None) -> bool:
    """Добавляет заявку в каталог."""
    try:
        await _retry_supabase_call(
            supabase.table("catalog_chats").upsert({
                "chat_id": chat_id,
                "category_id": category_id,
                "added_by": added_by,
                "link": link,
                "is_approved": False
            })
        )
        return True
    except Exception as e:
        logging.error(f"Ошибка при добавлении в каталог {chat_id}: {e}")
        return False

async def get_catalog_chat(chat_id: int) -> dict:
    """Получает данные чата в каталоге."""
    try:
        res = await _retry_supabase_call(
            supabase.table("catalog_chats").select("*").eq("chat_id", chat_id).limit(1)
        )
        return res.data[0] if res.data else None
    except Exception as e:
        logging.error(f"Ошибка при получении чата из каталога {chat_id}: {e}")
        return None

async def update_catalog_link(chat_id: int, link: str) -> bool:
    """Обновляет ссылку чата в каталоге."""
    try:
        await _retry_supabase_call(
            supabase.table("catalog_chats").update({"link": link}).eq("chat_id", chat_id)
        )
        return True
    except Exception as e:
        logging.error(f"Ошибка при обновлении ссылки каталога {chat_id}: {e}")
        return False

async def delete_catalog_link(chat_id: int) -> bool:
    """Удаляет ссылку чата из каталога (ставит NULL)."""
    try:
        await _retry_supabase_call(
            supabase.table("catalog_chats").update({"link": None}).eq("chat_id", chat_id)
        )
        return True
    except Exception as e:
        logging.error(f"Ошибка при удалении ссылки каталога {chat_id}: {e}")
        return False

async def get_approved_chats(category_id: int = None) -> List[dict]:
    """Возвращает список одобренных чатов."""
    try:
        query = supabase.table("catalog_chats").select("*").eq("is_approved", True)
        if category_id:
            query = query.eq("category_id", category_id)
        res = await _retry_supabase_call(query)
        return res.data or []
    except Exception as e:
        logging.error(f"Ошибка при получении одобренных чатов: {e}")
        return []
