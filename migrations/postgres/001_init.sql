-- =============================================================================
-- PostgreSQL: Инициализация схемы для Clickstream Analytics
-- =============================================================================

-- Таблица пользователей (справочник)
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(64) UNIQUE NOT NULL,
    fio VARCHAR(255),
    email VARCHAR(255),
    country CHAR(2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица страниц (справочник)
CREATE TABLE IF NOT EXISTS pages (
    id BIGSERIAL PRIMARY KEY,
    url VARCHAR(2048) UNIQUE NOT NULL,
    title VARCHAR(255),
    category VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица сессий
CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    user_id BIGINT REFERENCES users(id),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    device_type VARCHAR(20),
    browser VARCHAR(100),
    os VARCHAR(100),
    country CHAR(2),
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для ускорения запросов
CREATE INDEX IF NOT EXISTS idx_users_external_id ON users(external_id);
CREATE INDEX IF NOT EXISTS idx_users_country ON users(country);
CREATE INDEX IF NOT EXISTS idx_pages_category ON pages(category);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at);

-- Триггер для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Вставка тестовых данных для пользователей
INSERT INTO users (external_id, fio, email, country) VALUES
    ('user-001', 'Иванов Иван Иванович', 'ivanov@example.com', 'RU'),
    ('user-002', 'Петров Пётр Петрович', 'petrov@example.com', 'RU'),
    ('user-003', 'Сидорова Анна Сергеевна', 'sidorova@example.com', 'RU'),
    ('user-004', 'John Smith', 'john.smith@example.com', 'US'),
    ('user-005', 'Jane Doe', 'jane.doe@example.com', 'US'),
    ('user-006', 'Hans Mueller', 'hans.mueller@example.com', 'DE'),
    ('user-007', 'Pierre Dupont', 'pierre.dupont@example.com', 'FR'),
    ('user-008', 'Козлов Алексей Викторович', 'kozlov@example.com', 'RU'),
    ('user-009', 'Maria Garcia', 'maria.garcia@example.com', 'ES'),
    ('user-010', 'Yamamoto Taro', 'yamamoto@example.com', 'JP')
ON CONFLICT (external_id) DO NOTHING;

-- Вставка тестовых данных для страниц
INSERT INTO pages (url, title, category) VALUES
    ('/', 'Главная страница', 'main'),
    ('/catalog', 'Каталог товаров', 'catalog'),
    ('/catalog/electronics', 'Электроника', 'catalog'),
    ('/catalog/clothing', 'Одежда', 'catalog'),
    ('/catalog/books', 'Книги', 'catalog'),
    ('/product/1', 'iPhone 15 Pro', 'product'),
    ('/product/2', 'Samsung Galaxy S24', 'product'),
    ('/product/3', 'MacBook Pro 16', 'product'),
    ('/cart', 'Корзина', 'checkout'),
    ('/checkout', 'Оформление заказа', 'checkout'),
    ('/profile', 'Личный кабинет', 'user'),
    ('/orders', 'Мои заказы', 'user'),
    ('/about', 'О компании', 'info'),
    ('/contacts', 'Контакты', 'info'),
    ('/blog', 'Блог', 'content')
ON CONFLICT (url) DO NOTHING;

-- Комментарии к таблицам
COMMENT ON TABLE users IS 'Справочник пользователей системы';
COMMENT ON TABLE pages IS 'Справочник страниц сайта';
COMMENT ON TABLE sessions IS 'Информация о пользовательских сессиях';

COMMENT ON COLUMN users.external_id IS 'Внешний идентификатор пользователя';
COMMENT ON COLUMN users.fio IS 'ФИО пользователя';
COMMENT ON COLUMN users.country IS 'ISO-код страны (2 символа)';

COMMENT ON COLUMN pages.url IS 'URL страницы';
COMMENT ON COLUMN pages.title IS 'Заголовок страницы';
COMMENT ON COLUMN pages.category IS 'Категория страницы';

COMMENT ON COLUMN sessions.session_id IS 'Уникальный идентификатор сессии';
COMMENT ON COLUMN sessions.device_type IS 'Тип устройства: desktop, mobile, tablet';
