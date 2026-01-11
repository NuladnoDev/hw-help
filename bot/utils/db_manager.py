import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from aiogram import types
from supabase import create_client, Client
from bot.config_reader import config

# Инициализация клиента Supabase
supabase: Client = create_client(
    config.supabase_url, 
    config.supabase_key.get_secret_value()
)

# Кэш для активности
_activity_cache = {}
_CACHE_TTL = 300

# --- Users ---

async def update_user_cache(user_id: int, username: Optional[str], full_name: Optional[str] = None):
    data = {"user_id": user_id}
    if username:
        data["username"] = username.replace("@", "").lower()
    if full_name:
        data["full_name"] = full_name
    
    await asyncio.to_thread(supabase.table("users").upsert(data).execute)

async def get_username_by_id(user_id: int) -> Optional[str]:
    res = await asyncio.to_thread(supabase.table("users").select("username").eq("user_id", user_id).execute)
    if res.data:
        return res.data[0].get("username")
    return None

async def get_full_name_by_id(user_id: int) -> Optional[str]:
    res = await asyncio.to_thread(supabase.table("users").select("full_name").eq("user_id", user_id).execute)
    if res.data:
        return res.data[0].get("full_name")
    return None

async def get_user_id_by_username(username: str) -> Optional[int]:
    clean_username = username.replace("@", "").lower()
    res = await asyncio.to_thread(supabase.table("users").select("user_id").eq("username", clean_username).execute)
    if res.data:
        return res.data[0].get("user_id")
    return None

# --- Mutes & Bans ---

async def add_mute(chat_id: int, user_id: int, until_date: Optional[datetime] = None):
    until = until_date.isoformat() if until_date else None
    await asyncio.to_thread(supabase.table("mutes").upsert({
        "chat_id": chat_id,
        "user_id": user_id,
        "until": until
    }).execute)

async def remove_mute(chat_id: int, user_id: int):
    await asyncio.to_thread(supabase.table("mutes").delete().eq("chat_id", chat_id).eq("user_id", user_id).execute)

async def is_user_muted(chat_id: int, user_id: int) -> bool:
    res = await asyncio.to_thread(supabase.table("mutes").select("*").eq("chat_id", chat_id).eq("user_id", user_id).execute)
    if not res.data:
        return False
    
    until = res.data[0].get("until")
    if not until: # Permanent
        return True
    
    until_date = datetime.fromisoformat(until)
    if until_date > datetime.now(timezone.utc):
        return True
    
    await remove_mute(chat_id, user_id)
    return False

async def add_ban(chat_id: int, user_id: int, until_date: Optional[datetime] = None):
    until = until_date.isoformat() if until_date else None
    await asyncio.to_thread(supabase.table("bans").upsert({
        "chat_id": chat_id,
        "user_id": user_id,
        "until": until
    }).execute)

async def remove_ban(chat_id: int, user_id: int):
    await asyncio.to_thread(supabase.table("bans").delete().eq("chat_id", chat_id).eq("user_id", user_id).execute)

async def is_user_banned(chat_id: int, user_id: int) -> bool:
    res = await asyncio.to_thread(supabase.table("bans").select("*").eq("chat_id", chat_id).eq("user_id", user_id).execute)
    if not res.data:
        return False
    
    until = res.data[0].get("until")
    if not until: # Permanent
        return True
    
    until_date = datetime.fromisoformat(until)
    if until_date > datetime.now(timezone.utc):
        return True
    
    await remove_ban(chat_id, user_id)
    return False

# --- Warns ---

async def add_warn(chat_id: int, user_id: int, reason: str = "Не указана", until_date: Optional[datetime] = None):
    until = until_date.isoformat() if until_date else None
    await asyncio.to_thread(supabase.table("warns").insert({
        "chat_id": chat_id,
        "user_id": user_id,
        "reason": reason,
        "until": until
    }).execute)
    
    res = await asyncio.to_thread(supabase.table("warns").select("id", count="exact").eq("chat_id", chat_id).eq("user_id", user_id).execute)
    return len(res.data)

async def get_warns(chat_id: int, user_id: int) -> List[Dict]:
    res = await asyncio.to_thread(supabase.table("warns").select("*").eq("chat_id", chat_id).eq("user_id", user_id).execute)
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
        await asyncio.to_thread(supabase.table("warns").delete().in_("id", expired_ids).execute)
        
    return active_warns

async def remove_last_warn(chat_id: int, user_id: int) -> bool:
    res = await asyncio.to_thread(supabase.table("warns").select("id").eq("chat_id", chat_id).eq("user_id", user_id).order("id", desc=True).limit(1).execute)
    if res.data:
        await asyncio.to_thread(supabase.table("warns").delete().eq("id", res.data[0]["id"]).execute)
        return True
    return False

async def remove_warn_by_index(chat_id: int, user_id: int, index: int) -> bool:
    warns = await get_warns(chat_id, user_id)
    if 0 <= index < len(warns):
        await asyncio.to_thread(supabase.table("warns").delete().eq("id", warns[index]["id"]).execute)
        return True
    return False

async def clear_warns(chat_id: int, user_id: int) -> bool:
    await asyncio.to_thread(supabase.table("warns").delete().eq("chat_id", chat_id).eq("user_id", user_id).execute)
    return True

# --- Nicknames & Descriptions ---

async def set_nickname(user_id: int, nickname: str):
    await asyncio.to_thread(supabase.table("users").upsert({"user_id": user_id, "nickname": nickname}).execute)

async def remove_nickname(user_id: int) -> bool:
    await asyncio.to_thread(supabase.table("users").update({"nickname": None}).eq("user_id", user_id).execute)
    return True

async def get_nickname(user_id: int) -> Optional[str]:
    res = await asyncio.to_thread(supabase.table("users").select("nickname").eq("user_id", user_id).execute)
    if res.data:
        return res.data[0].get("nickname")
    return None

async def set_description(user_id: int, description: str):
    await asyncio.to_thread(supabase.table("users").upsert({"user_id": user_id, "description": description}).execute)

async def remove_description(user_id: int) -> bool:
    await asyncio.to_thread(supabase.table("users").update({"description": None}).eq("user_id", user_id).execute)
    return True

async def get_description(user_id: int) -> Optional[str]:
    res = await asyncio.to_thread(supabase.table("users").select("description").eq("user_id", user_id).execute)
    if res.data:
        return res.data[0].get("description")
    return None

# --- Awards ---

async def add_award(chat_id: int, target_user_id: int, admin_user_id: int, text: str) -> int:
    await asyncio.to_thread(supabase.table("awards").insert({
        "chat_id": chat_id,
        "user_id": target_user_id,
        "from_id": admin_user_id,
        "text": text
    }).execute)
    
    res = await asyncio.to_thread(supabase.table("awards").select("id", count="exact").eq("chat_id", chat_id).eq("user_id", target_user_id).execute)
    return len(res.data)

async def get_awards(chat_id: int, user_id: int) -> List[Dict]:
    res = await asyncio.to_thread(supabase.table("awards").select("*").eq("chat_id", chat_id).eq("user_id", user_id).execute)
    return res.data or []

async def remove_award_by_index(chat_id: int, user_id: int, index: int) -> bool:
    awards = await get_awards(chat_id, user_id)
    if 0 <= index < len(awards):
        await asyncio.to_thread(supabase.table("awards").delete().eq("id", awards[index]["id"]).execute)
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

async def get_rank(user_id: int, chat_id: int) -> Tuple[int, str]:
    if config.creator_id and user_id == config.creator_id:
        return 5, RANKS[5]
    
    res = await asyncio.to_thread(supabase.table("chat_members").select("rank").eq("chat_id", chat_id).eq("user_id", user_id).execute)
    if res.data:
        rank_level = res.data[0].get("rank", 1)
        return rank_level, RANKS.get(rank_level, "Неизвестно")
    
    return 1, RANKS[1]

async def set_rank(user_id: int, chat_id: int, rank_level: int) -> bool:
    if rank_level not in RANKS or rank_level < 1:
        return False
    await asyncio.to_thread(supabase.table("chat_members").upsert({
        "chat_id": chat_id,
        "user_id": user_id,
        "rank": rank_level
    }).execute)
    return True

async def get_user_rank_context(user_id: int, chat: types.Chat) -> Tuple[int, str, bool]:
    if config.creator_id and user_id == config.creator_id:
        return 5, RANKS[5], True
        
    try:
        member = await chat.get_member(user_id)
        if member.status == "creator":
            return 5, RANKS[5], True
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
    res = await asyncio.to_thread(supabase.table("chat_members").select("user_id", "rank").eq("chat_id", chat_id).execute)
    return {item["user_id"]: item["rank"] for item in res.data} if res.data else {}

# --- Invites ---

async def save_inviter(chat_id: int, user_id: int, inviter_id: int):
    await asyncio.to_thread(supabase.table("inviters").upsert({
        "chat_id": chat_id,
        "user_id": user_id,
        "inviter_id": inviter_id
    }).execute)

async def get_inviter(chat_id: int, user_id: int) -> Optional[int]:
    res = await asyncio.to_thread(supabase.table("inviters").select("inviter_id").eq("chat_id", chat_id).eq("user_id", user_id).execute)
    if res.data:
        return res.data[0].get("inviter_id")
    return None

# --- Marriages ---

async def create_marriage(user1_id: int, user2_id: int):
    u1, u2 = sorted([user1_id, user2_id])
    await asyncio.to_thread(supabase.table("marriages").upsert({
        "user1_id": u1,
        "user2_id": u2
    }).execute)

async def get_marriage(user_id: int) -> Optional[Dict]:
    res = await asyncio.to_thread(supabase.table("marriages").select("*").or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}").execute)
    if res.data:
        m = res.data[0]
        return {
            "partners": [m["user1_id"], m["user2_id"]],
            "created_at": m["created_at"]
        }
    return None

async def remove_marriage(user_id: int) -> bool:
    res = await asyncio.to_thread(supabase.table("marriages").delete().or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}").execute)
    return True if res.data else False

# --- Relationships ---

async def update_relationship(user1_id: int, user2_id: int, action_type: str) -> Dict:
    u1, u2 = sorted([int(user1_id), int(user2_id)])
    
    # Сначала получаем текущие данные
    res = await asyncio.to_thread(supabase.table("relationships").select("*").eq("user1_id", u1).eq("user2_id", u2).execute)
    
    if res.data:
        rel = res.data[0]
        actions = rel.get("actions", {})
        actions[action_type] = actions.get(action_type, 0) + 1
        total = rel.get("total_interactions", 0) + 1
    else:
        actions = {action_type: 1}
        total = 1
        
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
    await asyncio.to_thread(supabase.table("users").upsert({
        "user_id": user_id,
        "last_message": now_iso
    }).execute)
    
    _activity_cache[user_id] = now_ts

async def get_user_stats(user_id: int) -> Dict:
    res = await asyncio.to_thread(supabase.table("users").select("first_appearance", "last_message").eq("user_id", user_id).execute)
    if res.data:
        return res.data[0]
    return {
        "first_appearance": datetime.now(timezone.utc).isoformat(),
        "last_message": datetime.now(timezone.utc).isoformat()
    }

