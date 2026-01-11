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

async def _retry_supabase_call(query_builder, retries=3, delay=1):
    """
    Вспомогательная функция для повторных попыток запроса к Supabase при ошибках сети/SSL.
    """
    last_exception = None
    for attempt in range(retries):
        try:
            return await asyncio.to_thread(query_builder.execute)
        except (httpx.ConnectError, httpx.RemoteProtocolError, Exception) as e:
            last_exception = e
            if attempt < retries - 1:
                logging.warning(f"Попытка {attempt + 1} провалена: {e}. Повтор через {delay} сек...")
                await asyncio.sleep(delay)
                delay *= 2 # Экспоненциальное ожидание
    
    logging.error(f"Все {retries} попыток запроса провалены. Последняя ошибка: {last_exception}")
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
    except Exception:
        pass
    
    level, name = await get_rank(user_id, chat.id)
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
        
    new_data = {
        "user1_id": u1,
        "user2_id": u2,
        "total_interactions": total,
        "last_interaction": datetime.now(timezone.utc).isoformat(),
        "actions": actions
    }
    
    await asyncio.to_thread(supabase.table("relationships").upsert(new_data).execute)
    return new_data

async def get_relationship(user1_id: int, user2_id: int) -> Optional[Dict]:
    u1, u2 = sorted([int(user1_id), int(user2_id)])
    res = await asyncio.to_thread(supabase.table("relationships").select("*").eq("user1_id", u1).eq("user2_id", u2).execute)
    return res.data[0] if res.data else None

async def delete_relationship(user1_id: int, user2_id: int) -> bool:
    u1, u2 = sorted([int(user1_id), int(user2_id)])
    await asyncio.to_thread(supabase.table("relationships").delete().eq("user1_id", u1).eq("user2_id", u2).execute)
    return True

async def get_all_user_relationships(user_id: int) -> List[Dict]:
    res = await asyncio.to_thread(supabase.table("relationships").select("*").or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}").execute)
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
        await asyncio.to_thread(supabase.table("users").upsert({
            "user_id": user_id,
            "last_message": now_iso
        }).execute)
        
        today = datetime.now(timezone.utc).date().isoformat()
        res = await asyncio.to_thread(
            supabase.table("activity_stats")
            .select("count")
            .eq("user_id", user_id)
            .eq("date", today)
            .execute
        )
        if res.data:
            current = res.data[0].get("count", 0) or 0
            await asyncio.to_thread(
                supabase.table("activity_stats")
                .update({"count": current + 1})
                .eq("user_id", user_id)
                .eq("date", today)
                .execute
            )
        else:
            await asyncio.to_thread(
                supabase.table("activity_stats")
                .insert({"user_id": user_id, "date": today, "count": 1})
                .execute
            )
        
        _activity_cache[user_id] = now_ts
    except Exception as e:
        logging.warning(f"Ошибка при обновлении активности (RLS/DB): {e}")

async def get_user_stats(user_id: int) -> Dict:
    res = await asyncio.to_thread(supabase.table("users").select("first_appearance", "last_message").eq("user_id", user_id).execute)
    if res.data:
        return res.data[0]
    return {
        "first_appearance": datetime.now(timezone.utc).isoformat(),
        "last_message": datetime.now(timezone.utc).isoformat()
    }

async def get_user_activity_series(user_id: int, days: int = 30) -> List[Tuple[datetime, int]]:
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)
    
    res = await asyncio.to_thread(
        supabase.table("activity_stats")
        .select("date,count")
        .eq("user_id", user_id)
        .gte("date", start_date.isoformat())
        .order("date")
        .execute
    )
    
    raw = {datetime.fromisoformat(item["date"]).date(): item.get("count", 0) for item in (res.data or [])}
    
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
    res = await asyncio.to_thread(
        supabase.table("activity_stats")
        .select("count")
        .eq("user_id", user_id)
        .execute
    )
    if res.data:
        summary["total"] = sum(item.get("count", 0) or 0 for item in res.data)
            
    return summary

# --- Group Settings ---

async def set_welcome_message(chat_id: int, message_text: str):
    """Сохраняет текст приветствия для группы."""
    try:
        await asyncio.to_thread(
            supabase.table("group_settings").upsert({
                "chat_id": chat_id,
                "welcome_message": message_text
            }).execute
        )
    except Exception as e:
        logging.error(f"Ошибка при сохранении приветствия: {e}")

async def get_welcome_message(chat_id: int) -> Optional[str]:
    """Получает текст приветствия для группы."""
    try:
        res = await asyncio.to_thread(
            supabase.table("group_settings").select("welcome_message").eq("chat_id", chat_id).execute
        )
        if res.data:
            return res.data[0].get("welcome_message")
    except Exception as e:
        logging.error(f"Ошибка при получении приветствия: {e}")
    return None

async def get_disabled_modules(chat_id: int) -> List[str]:
    """Возвращает список идентификаторов выключенных модулей для чата."""
    try:
        res = await asyncio.to_thread(
            supabase.table("group_settings").select("disabled_modules").eq("chat_id", chat_id).execute
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
