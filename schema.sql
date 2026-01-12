-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    nickname TEXT,
    description TEXT,
    first_appearance TIMESTAMPTZ DEFAULT NOW(),
    last_message TIMESTAMPTZ DEFAULT NOW()
);

-- Таблица участников чатов (ранги)
CREATE TABLE IF NOT EXISTS chat_members (
    chat_id BIGINT,
    user_id BIGINT,
    rank INT DEFAULT 1,
    PRIMARY KEY (chat_id, user_id)
);

-- Баны
CREATE TABLE IF NOT EXISTS bans (
    chat_id BIGINT,
    user_id BIGINT,
    until TIMESTAMPTZ, -- NULL для перманентного
    PRIMARY KEY (chat_id, user_id)
);

-- Муты
CREATE TABLE IF NOT EXISTS mutes (
    chat_id BIGINT,
    user_id BIGINT,
    until TIMESTAMPTZ, -- NULL для перманентного
    PRIMARY KEY (chat_id, user_id)
);

-- Варны
CREATE TABLE IF NOT EXISTS warns (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT,
    user_id BIGINT,
    reason TEXT DEFAULT 'Не указана',
    date TIMESTAMPTZ DEFAULT NOW(),
    until TIMESTAMPTZ -- NULL для перманентного
);

-- Награды
CREATE TABLE IF NOT EXISTS awards (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT,
    user_id BIGINT,
    from_id BIGINT,
    text TEXT,
    date TIMESTAMPTZ DEFAULT NOW()
);

-- Инвайтеры
CREATE TABLE IF NOT EXISTS inviters (
    chat_id BIGINT,
    user_id BIGINT,
    inviter_id TEXT, -- Может быть ID пользователя или 'link'
    PRIMARY KEY (chat_id, user_id)
);

-- Браки
CREATE TABLE IF NOT EXISTS marriages (
    user1_id BIGINT PRIMARY KEY,
    user2_id BIGINT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Отношения
CREATE TABLE IF NOT EXISTS relationships (
    user1_id BIGINT,
    user2_id BIGINT,
    total_interactions INT DEFAULT 0,
    last_interaction TIMESTAMPTZ DEFAULT NOW(),
    actions JSONB DEFAULT '{}'::jsonb,
    PRIMARY KEY (user1_id, user2_id)
);

-- Кланы
CREATE TABLE IF NOT EXISTS clans (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT,
    name TEXT,
    creator_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (chat_id, name)
);

-- Участники кланов
CREATE TABLE IF NOT EXISTS clan_members (
    chat_id BIGINT,
    clan_id INT REFERENCES clans(id) ON DELETE CASCADE,
    user_id BIGINT,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (chat_id, user_id)
);

-- Кружки
CREATE TABLE IF NOT EXISTS clubs (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT,
    name TEXT,
    creator_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (chat_id, name)
);

-- Участники кружков
CREATE TABLE IF NOT EXISTS club_members (
    chat_id BIGINT,
    club_id INT REFERENCES clubs(id) ON DELETE CASCADE,
    user_id BIGINT,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (chat_id, club_id, user_id)
);

-- Статистика активности по дням
CREATE TABLE IF NOT EXISTS activity_stats (
    user_id BIGINT,
    date DATE,
    count INT DEFAULT 0,
    PRIMARY KEY (user_id, date)
);

-- Репутация
CREATE TABLE IF NOT EXISTS reputation (
    chat_id BIGINT,
    user_id BIGINT,
    points INT DEFAULT 0,
    plus_count INT DEFAULT 0,
    minus_count INT DEFAULT 0,
    PRIMARY KEY (chat_id, user_id)
);

-- Настройки групп
CREATE TABLE IF NOT EXISTS group_settings (
    chat_id BIGINT PRIMARY KEY,
    welcome_message TEXT,
    disabled_modules JSONB DEFAULT '[]'::jsonb,
    permission_settings JSONB DEFAULT '{}'::jsonb
);

-- Кастомные названия рангов для групп
CREATE TABLE IF NOT EXISTS group_ranks (
    chat_id BIGINT,
    rank_number INT,
    name_nom TEXT, -- Именительный (Кто?)
    name_gen TEXT, -- Родительный (Кого?)
    name_ins TEXT, -- Творительный (Кем?)
    PRIMARY KEY (chat_id, rank_number)
);

-- HW-Антиспам: Жалобы
CREATE TABLE IF NOT EXISTS antispam_reports (
    id SERIAL PRIMARY KEY,
    reporter_id BIGINT,
    target_id BIGINT,
    chat_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HW-Антиспам: Черный список
CREATE TABLE IF NOT EXISTS antispam_blacklist (
    user_id BIGINT PRIMARY KEY,
    reason TEXT DEFAULT 'Спам (HW-Антиспам)',
    added_at TIMESTAMPTZ DEFAULT NOW()
);

-- ВАЖНО: Отключите RLS для этих таблиц в Supabase SQL Editor, если возникают ошибки 42501:
-- ALTER TABLE antispam_reports DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE antispam_blacklist DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE group_ranks DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE group_settings DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE chat_members DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE users DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE warns DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE mutes DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE bans DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE awards DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE marriages DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE inviters DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE relationships DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE clans DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE clan_members DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE clubs DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE club_members DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE reputation DISABLE ROW LEVEL SECURITY;
