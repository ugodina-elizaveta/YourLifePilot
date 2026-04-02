-- Создание расширения для UUID (если понадобится)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ
-- Хранит основную информацию о пользователях бота
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,                                             -- Telegram user ID
    username TEXT,                                                            -- Telegram username (без @)
    first_name TEXT,                                                          -- Имя пользователя
    last_name TEXT,                                                           -- Фамилия пользователя
    language_code TEXT,                                                       -- Код языка (ru, en, etc.)
    is_bot BOOLEAN DEFAULT FALSE,                                             -- Является ли пользователь ботом
    onboarding_complete BOOLEAN DEFAULT FALSE,                                -- Завершен ли онбординг
    scenario JSONB DEFAULT '[]',                                              -- Сценарии пользователя ['ложусь поздно', 'просыпаюсь разбитым', ...]
    answers JSONB DEFAULT '{}',                                               -- Ответы на вопросы онбординга
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,            -- Дата регистрации
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,           -- Последняя активность
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP             -- Дата обновления
);
COMMENT ON TABLE users IS 'Пользователи бота';
COMMENT ON COLUMN users.user_id IS 'Уникальный идентификатор пользователя в Telegram';
COMMENT ON COLUMN users.username IS 'Имя пользователя в Telegram (без @)';
COMMENT ON COLUMN users.first_name IS 'Имя пользователя';
COMMENT ON COLUMN users.last_name IS 'Фамилия пользователя';
COMMENT ON COLUMN users.language_code IS 'Код языка интерфейса пользователя';
COMMENT ON COLUMN users.is_bot IS 'Флаг: true если это бот, false если реальный пользователь';
COMMENT ON COLUMN users.onboarding_complete IS 'Флаг завершения онбординга';
COMMENT ON COLUMN users.scenario IS 'Массив сценариев пользователя (ложусь поздно, просыпаюсь разбитым и т.д.)';
COMMENT ON COLUMN users.answers IS 'JSON с ответами на вопросы онбординга';
COMMENT ON COLUMN users.created_at IS 'Дата и время регистрации';
COMMENT ON COLUMN users.last_active IS 'Дата и время последней активности';
COMMENT ON COLUMN users.updated_at IS 'Дата и время последнего обновления';

CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_onboarding ON users(onboarding_complete);

-- =====================================================
-- ТАБЛИЦА СТАТИСТИКИ ПОЛЬЗОВАТЕЛЕЙ (STREAKS)
-- Хранит информацию о сериях успехов и пропусков
-- =====================================================
CREATE TABLE IF NOT EXISTS user_stats (
    id SERIAL PRIMARY KEY,
    user_id TEXT UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,     -- Ссылка на пользователя
    morning_streak INTEGER DEFAULT 0,                                    -- Дней подряд с выполненной утренней задачей
    morning_skip_streak INTEGER DEFAULT 0,                               -- Дней подряд с пропуском утренней задачи
    evening_streak INTEGER DEFAULT 0,                                    -- Дней подряд с выполненной вечерней задачей
    evening_skip_streak INTEGER DEFAULT 0,                               -- Дней подряд с пропуском вечерней задачи
    day_stress_streak INTEGER DEFAULT 0,                                 -- Дней подряд с выполненной антистресс-задачей
    day_stress_skip_streak INTEGER DEFAULT 0,                            -- Дней подряд с пропуском антистресс-задачи
    last_morning_date DATE,                                              -- Дата последнего утреннего действия
    last_evening_date DATE,                                              -- Дата последнего вечернего действия
    last_stress_date DATE,                                               -- Дата последнего антистресс-действия
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP        -- Дата обновления
);

COMMENT ON TABLE user_stats IS 'Статистика серий (streak) пользователя';
COMMENT ON COLUMN user_stats.user_id IS 'ID пользователя (внешний ключ к users)';
COMMENT ON COLUMN user_stats.morning_streak IS 'Количество дней подряд с выполненной утренней задачей';
COMMENT ON COLUMN user_stats.morning_skip_streak IS 'Количество дней подряд с пропуском утренней задачи';
COMMENT ON COLUMN user_stats.evening_streak IS 'Количество дней подряд с выполненной вечерней задачей';
COMMENT ON COLUMN user_stats.evening_skip_streak IS 'Количество дней подряд с пропуском вечерней задачи';
COMMENT ON COLUMN user_stats.day_stress_streak IS 'Количество дней подряд с выполненной антистресс-задачей';
COMMENT ON COLUMN user_stats.day_stress_skip_streak IS 'Количество дней подряд с пропуском антистресс-задачи';
COMMENT ON COLUMN user_stats.last_morning_date IS 'Дата последнего утреннего взаимодействия';
COMMENT ON COLUMN user_stats.last_evening_date IS 'Дата последнего вечернего взаимодействия';
COMMENT ON COLUMN user_stats.last_stress_date IS 'Дата последнего антистресс-взаимодействия';

CREATE INDEX IF NOT EXISTS idx_stats_user_id ON user_stats(user_id);

-- =====================================================
-- ТАБЛИЦА ИСТОРИИ НАСТРОЕНИЯ
-- Хранит историю ответов на вопрос "Как ты себя чувствуешь?"
-- =====================================================
CREATE TABLE IF NOT EXISTS mood_history (
    id SERIAL PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,      -- Ссылка на пользователя
    feeling TEXT NOT NULL,                                         -- Эмоция (Спокойно, Напряжён, Грустно, Очень плохо)
    note TEXT,                                                     -- Дополнительные заметки (опционально)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP  -- Дата и время записи
);

COMMENT ON TABLE mood_history IS 'История настроения пользователя';
COMMENT ON COLUMN mood_history.user_id IS 'ID пользователя (внешний ключ к users)';
COMMENT ON COLUMN mood_history.feeling IS 'Выбранная эмоция (Спокойно/Напряжён/Грустно/Очень плохо)';
COMMENT ON COLUMN mood_history.note IS 'Дополнительный комментарий пользователя';
COMMENT ON COLUMN mood_history.created_at IS 'Дата и время записи настроения';

CREATE INDEX IF NOT EXISTS idx_mood_user_id ON mood_history(user_id);
CREATE INDEX IF NOT EXISTS idx_mood_created_at ON mood_history(created_at);

-- =====================================================
-- ТАБЛИЦА ДЕЙСТВИЙ ПОЛЬЗОВАТЕЛЯ
-- Хранит все взаимодействия пользователя с ботом
-- =====================================================
CREATE TABLE IF NOT EXISTS user_actions (
    id SERIAL PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,        -- Ссылка на пользователя
    action_type TEXT NOT NULL,                                       -- Тип действия: 'morning', 'evening', 'stress', 'micro', 'onboarding', 'feeling'
    action_result TEXT NOT NULL,                                     -- Результат: 'normal', 'broken', 'done', 'skipped', 'completed', etc.
    details JSONB DEFAULT '{}',                                      -- Дополнительные детали в JSON формате
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP    -- Дата и время действия
);

COMMENT ON TABLE user_actions IS 'Лог всех действий пользователя в боте';
COMMENT ON COLUMN user_actions.user_id IS 'ID пользователя (внешний ключ к users)';
COMMENT ON COLUMN user_actions.action_type IS 'Тип действия (morning/evening/stress/micro/onboarding/feeling)';
COMMENT ON COLUMN user_actions.action_result IS 'Результат действия (normal/broken/done/skipped/completed и т.д.)';
COMMENT ON COLUMN user_actions.details IS 'Дополнительные данные в формате JSON';
COMMENT ON COLUMN user_actions.created_at IS 'Дата и время действия';

CREATE INDEX IF NOT EXISTS idx_actions_user_id ON user_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_actions_created_at ON user_actions(created_at);
CREATE INDEX IF NOT EXISTS idx_actions_type ON user_actions(action_type);

-- =====================================================
-- ФУНКЦИЯ АВТОМАТИЧЕСКОГО ОБНОВЛЕНИЯ updated_at
-- Автоматически обновляет поле updated_at при изменении записи
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

COMMENT ON FUNCTION update_updated_at_column IS 'Триггерная функция для автоматического обновления поля updated_at';

-- =====================================================
-- ТРИГГЕРЫ
-- Автоматически вызывают функцию update_updated_at_column
-- при обновлении записей
-- =====================================================

-- Триггер для таблицы users
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TRIGGER update_users_updated_at ON users IS 'Автоматически обновляет updated_at при изменении пользователя';

-- Триггер для таблицы user_stats
DROP TRIGGER IF EXISTS update_stats_updated_at ON user_stats;
CREATE TRIGGER update_stats_updated_at
    BEFORE UPDATE ON user_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TRIGGER update_stats_updated_at ON user_stats IS 'Автоматически обновляет updated_at при изменении статистики';

-- Таблица для хранения диалогов AI-чата
CREATE TABLE IF NOT EXISTS ai_chat_history (
    id SERIAL PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,                      -- Идентификатор сессии (UUID)
    message TEXT NOT NULL,                         -- Текст сообщения
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),  -- user или assistant
    metadata JSONB DEFAULT '{}',                   -- Дополнительные данные (настроение, тема)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_ai_chat_user_id ON ai_chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_session_id ON ai_chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_created_at ON ai_chat_history(created_at);

-- Комментарии
COMMENT ON TABLE ai_chat_history IS 'История диалогов в режиме AI-чата';
COMMENT ON COLUMN ai_chat_history.session_id IS 'Идентификатор сессии диалога (один сеанс чата)';
COMMENT ON COLUMN ai_chat_history.role IS 'Роль отправителя: user или assistant';
COMMENT ON COLUMN ai_chat_history.metadata IS 'Дополнительные метаданные (настроение пользователя, определённая ситуация)';
