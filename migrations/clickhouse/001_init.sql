-- =============================================================================
-- ClickHouse: Инициализация схемы для Clickstream Analytics
-- =============================================================================

-- Создание базы данных
CREATE DATABASE IF NOT EXISTS clickstream;

-- =============================================================================
-- ТАБЛИЦА: events_raw (сырые события)
-- =============================================================================
CREATE TABLE IF NOT EXISTS clickstream.events_raw
(
    id UInt64,
    event_type String,
    created_at DateTime,
    received_at DateTime,
    session_id String,
    ip String,
    user_id UInt64,
    url String,
    referrer String,
    device_type String,
    user_agent String,
    payload String,
    source String,
    country String DEFAULT ''
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/events_raw', '{replica}')
PARTITION BY toYYYYMM(created_at)
ORDER BY (created_at, user_id, id)
TTL created_at + INTERVAL 1 YEAR
SETTINGS index_granularity = 8192;

-- =============================================================================
-- ТАБЛИЦА: events_processed (обработанные события)
-- =============================================================================
CREATE TABLE IF NOT EXISTS clickstream.events_processed
(
    id UInt64,
    event_type String,
    event_date Date,
    event_hour UInt8,
    created_at DateTime,
    session_id String,
    user_id UInt64,
    url String,
    url_path String,
    referrer String,
    device_type String,
    country String,
    browser String,
    browser_version String,
    os String,
    os_version String,
    event_title String,
    element_id String,
    x UInt32,
    y UInt32,
    is_bot UInt8 DEFAULT 0
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/events_processed', '{replica}')
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, user_id, session_id, created_at)
TTL event_date + INTERVAL 2 YEAR
SETTINGS index_granularity = 8192;

-- =============================================================================
-- ВИТРИНА: daily_stats (ежедневная статистика)
-- =============================================================================
CREATE TABLE IF NOT EXISTS clickstream.daily_stats
(
    date Date,
    total_events UInt64,
    total_views UInt64,
    total_clicks UInt64,
    unique_users UInt64,
    unique_sessions UInt64,
    avg_session_duration_sec Float64,
    avg_events_per_session Float64,
    bounce_rate Float64,
    calculated_at DateTime DEFAULT now()
)
ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/daily_stats', '{replica}', calculated_at)
ORDER BY date
SETTINGS index_granularity = 8192;

-- =============================================================================
-- ВИТРИНА: page_stats (статистика по страницам)
-- =============================================================================
CREATE TABLE IF NOT EXISTS clickstream.page_stats
(
    date Date,
    url String,
    url_path String,
    views UInt64,
    clicks UInt64,
    unique_users UInt64,
    unique_sessions UInt64,
    avg_time_on_page_sec Float64,
    conversion_rate Float64,
    calculated_at DateTime DEFAULT now()
)
ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/page_stats', '{replica}', calculated_at)
ORDER BY (date, url)
SETTINGS index_granularity = 8192;

-- =============================================================================
-- ВИТРИНА: hourly_stats (почасовая статистика)
-- =============================================================================
CREATE TABLE IF NOT EXISTS clickstream.hourly_stats
(
    date Date,
    hour UInt8,
    total_events UInt64,
    total_views UInt64,
    total_clicks UInt64,
    unique_users UInt64,
    calculated_at DateTime DEFAULT now()
)
ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/hourly_stats', '{replica}', calculated_at)
ORDER BY (date, hour)
SETTINGS index_granularity = 8192;

-- =============================================================================
-- ВИТРИНА: device_stats (статистика по устройствам)
-- =============================================================================
CREATE TABLE IF NOT EXISTS clickstream.device_stats
(
    date Date,
    device_type String,
    browser String,
    os String,
    events_count UInt64,
    unique_users UInt64,
    unique_sessions UInt64,
    calculated_at DateTime DEFAULT now()
)
ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/device_stats', '{replica}', calculated_at)
ORDER BY (date, device_type, browser, os)
SETTINGS index_granularity = 8192;

-- =============================================================================
-- ВИТРИНА: element_stats (статистика по элементам - для heatmap)
-- =============================================================================
CREATE TABLE IF NOT EXISTS clickstream.element_stats
(
    date Date,
    url String,
    element_id String,
    event_title String,
    clicks UInt64,
    unique_users UInt64,
    avg_x Float64,
    avg_y Float64,
    calculated_at DateTime DEFAULT now()
)
ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/element_stats', '{replica}', calculated_at)
ORDER BY (date, url, element_id)
SETTINGS index_granularity = 8192;

-- =============================================================================
-- ВИТРИНА: user_activity (активность пользователей DAU/WAU/MAU)
-- =============================================================================
CREATE TABLE IF NOT EXISTS clickstream.user_activity
(
    date Date,
    dau UInt64,
    wau UInt64,
    mau UInt64,
    new_users UInt64,
    returning_users UInt64,
    calculated_at DateTime DEFAULT now()
)
ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/user_activity', '{replica}', calculated_at)
ORDER BY date
SETTINGS index_granularity = 8192;

-- =============================================================================
-- ВИТРИНА: session_stats (статистика сессий)
-- =============================================================================
CREATE TABLE IF NOT EXISTS clickstream.session_stats
(
    date Date,
    session_id String,
    user_id UInt64,
    device_type String,
    country String,
    start_time DateTime,
    end_time DateTime,
    duration_sec UInt32,
    events_count UInt32,
    pages_viewed UInt32,
    clicks_count UInt32,
    is_bounce UInt8
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/session_stats', '{replica}')
PARTITION BY toYYYYMM(date)
ORDER BY (date, user_id, session_id)
SETTINGS index_granularity = 8192;

-- =============================================================================
-- MATERIALIZED VIEW: для автоматического обновления hourly_stats
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS clickstream.mv_hourly_stats
TO clickstream.hourly_stats
AS
SELECT
    toDate(created_at) AS date,
    toHour(created_at) AS hour,
    count() AS total_events,
    countIf(event_type = 'view') AS total_views,
    countIf(event_type = 'click') AS total_clicks,
    uniq(user_id) AS unique_users,
    now() AS calculated_at
FROM clickstream.events_processed
GROUP BY date, hour;

-- =============================================================================
-- MATERIALIZED VIEW: для автоматического обновления device_stats
-- =============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS clickstream.mv_device_stats
TO clickstream.device_stats
AS
SELECT
    toDate(created_at) AS date,
    device_type,
    browser,
    os,
    count() AS events_count,
    uniq(user_id) AS unique_users,
    uniq(session_id) AS unique_sessions,
    now() AS calculated_at
FROM clickstream.events_processed
GROUP BY date, device_type, browser, os;
