-- ШПАРГАЛКА ПО SQL ДЛЯ УПРАВЛЕНИЯ БАЛАНСОМ И КАТАЛОГОМ --

-- 1. УПРАВЛЕНИЕ БАЛАНСОМ ЧАТА (для каталога)
-- Заменить <CHAT_ID> на ID группы (например, -100123456789)

-- Посмотреть баланс чата:
SELECT * FROM chat_economy WHERE chat_id = <CHAT_ID>;

-- Установить баланс чата (например, 35000):
INSERT INTO chat_economy (chat_id, coins) 
VALUES (<CHAT_ID>, 35000)
ON CONFLICT (chat_id) DO UPDATE SET coins = 35000;

-- Добавить койны к текущему балансу чата:
UPDATE chat_economy SET coins = coins + 5000 WHERE chat_id = <CHAT_ID>;


-- 2. УПРАВЛЕНИЕ БАЛАНСОМ ПОЛЬЗОВАТЕЛЯ (личные койны)
-- Заменить <USER_ID> на ID пользователя

-- Посмотреть баланс пользователя:
SELECT * FROM economy WHERE user_id = <USER_ID>;

-- Установить баланс пользователя:
INSERT INTO economy (user_id, coins) 
VALUES (<USER_ID>, 100000)
ON CONFLICT (user_id) DO UPDATE SET coins = 100000;


-- 3. МОДЕРАЦИЯ КАТАЛОГА

-- Одобрить чат в каталоге:
UPDATE catalog_chats SET is_approved = TRUE WHERE chat_id = <CHAT_ID>;

-- Убрать чат из каталога (отклонить/скрыть):
UPDATE catalog_chats SET is_approved = FALSE WHERE chat_id = <CHAT_ID>;

-- Посмотреть все заявки, которые ждут одобрения:
SELECT * FROM catalog_chats WHERE is_approved = FALSE;


-- 4. УПРАВЛЕНИЕ КАТЕГОРИЯМИ

-- Добавить новую категорию:
INSERT INTO catalog_categories (name) VALUES ('Игры'), ('Общение'), ('Обучение');

-- Посмотреть все категории:
SELECT * FROM catalog_categories;


-- 5. УПРАВЛЕНИЕ УРОВНЯМИ (XP и Level)
-- Заменить <USER_ID> на ID пользователя

-- Создать таблицу уровней (если еще не создана):
CREATE TABLE IF NOT EXISTS user_levels (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    level INT DEFAULT 0,
    xp BIGINT DEFAULT 0,
    has_marriage_bonus BOOLEAN DEFAULT FALSE,
    has_clan_bonus BOOLEAN DEFAULT FALSE,
    has_club_bonus BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Посмотреть уровень и опыт пользователя:
SELECT * FROM user_levels WHERE user_id = <USER_ID>;

-- Установить конкретный уровень и опыт:
INSERT INTO user_levels (user_id, level, xp) 
VALUES (<USER_ID>, 5, 0)
ON CONFLICT (user_id) DO UPDATE SET level = 5, xp = 0;

-- Сбросить одноразовые бонусы (чтобы пользователь мог получить их снова):
UPDATE user_levels 
SET has_marriage_bonus = FALSE, has_clan_bonus = FALSE, has_club_bonus = FALSE 
WHERE user_id = <USER_ID>;
