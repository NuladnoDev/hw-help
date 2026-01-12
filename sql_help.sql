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
