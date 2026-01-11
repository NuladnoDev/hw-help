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

-- Статистика активности по дням
CREATE TABLE IF NOT EXISTS activity_stats (
    user_id BIGINT,
    date DATE,
    count INT DEFAULT 0,
    PRIMARY KEY (user_id, date)
);

-- Настройки групп
CREATE TABLE IF NOT EXISTS group_settings (
    chat_id BIGINT PRIMARY KEY,
    welcome_message TEXT,
    disabled_modules JSONB DEFAULT '[]'::jsonb,
    permission_settings JSONB DEFAULT '{}'::jsonb
);
