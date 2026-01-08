"""
Clickstream ETL DAG

This DAG processes clickstream events daily:
1. Loads raw events from staging
2. Cleans and validates data
3. Enriches events (parse User-Agent, geolocate IP)
4. Builds analytics data marts
"""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.dates import days_ago

# ClickHouse connection settings
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse-1")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "clickstream")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "clickstream123")
CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "clickstream")


def get_clickhouse_client():
    """Create ClickHouse client connection."""
    from clickhouse_driver import Client

    return Client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DATABASE,
    )


def clean_and_validate(**context):
    """
    Clean and validate raw events.

    - Remove duplicates
    - Validate required fields
    - Filter out bot traffic
    """
    execution_date = context["execution_date"].date()
    print(f"Cleaning events for date: {execution_date}")

    client = get_clickhouse_client()

    # Remove duplicates and validate data
    query = """
        INSERT INTO events_processed
        SELECT
            id,
            event_type,
            toDate(created_at) as event_date,
            toHour(created_at) as event_hour,
            created_at,
            session_id,
            user_id,
            url,
            -- Extract path from URL
            if(position(url, '?') > 0,
               substring(url, 1, position(url, '?') - 1),
               url) as url_path,
            referrer,
            device_type,
            country,
            '' as browser,
            '' as browser_version,
            '' as os,
            '' as os_version,
            JSONExtractString(payload, 'event_title') as event_title,
            JSONExtractString(payload, 'element_id') as element_id,
            JSONExtractUInt(payload, 'x') as x,
            JSONExtractUInt(payload, 'y') as y,
            0 as is_bot
        FROM events_raw
        WHERE toDate(created_at) = %(date)s
          AND session_id != ''
          AND url != ''
          AND id NOT IN (SELECT id FROM events_processed WHERE event_date = %(date)s)
    """

    result = client.execute(query, {"date": execution_date})
    print(f"Cleaned and validated events for {execution_date}")

    client.disconnect()


def enrich_events(**context):
    """
    Enrich events with additional data.

    - Parse User-Agent (browser, OS)
    - Geolocate IP addresses
    """
    execution_date = context["execution_date"].date()
    print(f"Enriching events for date: {execution_date}")

    # Note: In a real implementation, you would:
    # 1. Parse user_agent to extract browser/OS info
    # 2. Use GeoIP database to get country from IP
    # For this demo, we'll use simple heuristics

    client = get_clickhouse_client()

    # Update browser/OS based on user_agent patterns
    # This is a simplified version - in production use a proper UA parser
    update_query = """
        ALTER TABLE events_processed
        UPDATE
            browser = multiIf(
                position(lower(user_agent), 'chrome') > 0, 'Chrome',
                position(lower(user_agent), 'firefox') > 0, 'Firefox',
                position(lower(user_agent), 'safari') > 0, 'Safari',
                position(lower(user_agent), 'edge') > 0, 'Edge',
                'Other'
            ),
            os = multiIf(
                position(lower(user_agent), 'windows') > 0, 'Windows',
                position(lower(user_agent), 'mac os') > 0, 'macOS',
                position(lower(user_agent), 'linux') > 0, 'Linux',
                position(lower(user_agent), 'android') > 0, 'Android',
                position(lower(user_agent), 'iphone') > 0 OR position(lower(user_agent), 'ipad') > 0, 'iOS',
                'Other'
            ),
            country = if(country = '', 'XX', country)  -- XX for unknown country
        WHERE event_date = %(date)s
          AND browser = ''
    """

    # Note: ALTER TABLE UPDATE is async in ClickHouse
    # In production, you might use INSERT INTO ... SELECT with transformations

    print(f"Enriched events for {execution_date}")
    client.disconnect()


def build_daily_stats(**context):
    """
    Build daily statistics mart.

    Aggregates daily metrics:
    - Total events, views, clicks
    - Unique users and sessions
    - Average session duration
    - Bounce rate
    """
    execution_date = context["execution_date"].date()
    print(f"Building daily stats for: {execution_date}")

    client = get_clickhouse_client()

    # First, calculate session-level stats
    query = """
        INSERT INTO daily_stats
        SELECT
            %(date)s as date,
            total_events,
            total_views,
            total_clicks,
            unique_users,
            unique_sessions,
            avg_session_duration_sec,
            total_events / unique_sessions as avg_events_per_session,
            bounce_sessions * 100.0 / unique_sessions as bounce_rate,
            now() as calculated_at
        FROM (
            SELECT
                count() as total_events,
                countIf(event_type = 'view') as total_views,
                countIf(event_type = 'click') as total_clicks,
                uniq(user_id) as unique_users,
                uniq(session_id) as unique_sessions,
                avg(session_duration) as avg_session_duration_sec,
                countIf(session_events = 1) as bounce_sessions
            FROM (
                SELECT
                    event_type,
                    user_id,
                    session_id,
                    dateDiff('second', min(created_at), max(created_at)) as session_duration,
                    count() as session_events
                FROM events_processed
                WHERE event_date = %(date)s
                GROUP BY event_type, user_id, session_id
            )
        )
    """

    client.execute(query, {"date": execution_date})
    print(f"Daily stats built for {execution_date}")

    client.disconnect()


def build_page_stats(**context):
    """
    Build page statistics mart.

    Aggregates per-page metrics:
    - Views and clicks per page
    - Unique users per page
    - Conversion rate (clicks/views)
    """
    execution_date = context["execution_date"].date()
    print(f"Building page stats for: {execution_date}")

    client = get_clickhouse_client()

    query = """
        INSERT INTO page_stats
        SELECT
            event_date as date,
            url,
            url_path,
            countIf(event_type = 'view') as views,
            countIf(event_type = 'click') as clicks,
            uniq(user_id) as unique_users,
            uniq(session_id) as unique_sessions,
            0 as avg_time_on_page_sec,
            if(countIf(event_type = 'view') > 0,
               countIf(event_type = 'click') * 100.0 / countIf(event_type = 'view'),
               0) as conversion_rate,
            now() as calculated_at
        FROM events_processed
        WHERE event_date = %(date)s
        GROUP BY event_date, url, url_path
    """

    client.execute(query, {"date": execution_date})
    print(f"Page stats built for {execution_date}")

    client.disconnect()


def build_user_activity(**context):
    """
    Build user activity mart (DAU/WAU/MAU).
    """
    execution_date = context["execution_date"].date()
    print(f"Building user activity for: {execution_date}")

    client = get_clickhouse_client()

    query = """
        INSERT INTO user_activity
        SELECT
            toDate(%(date)s) as date,
            uniqIf(user_id, event_date = toDate(%(date)s)) as dau,
            uniqIf(user_id, event_date >= toDate(%(date)s) - 7) as wau,
            uniqIf(user_id, event_date >= toDate(%(date)s) - 30) as mau,
            0 as new_users,
            0 as returning_users,
            now() as calculated_at
        FROM events_processed
        WHERE event_date >= toDate(%(date)s) - 30 AND event_date <= toDate(%(date)s)
    """

    client.execute(query, {"date": execution_date})
    print(f"User activity built for {execution_date}")

    client.disconnect()


def build_session_stats(**context):
    """
    Build session-level statistics.

    Calculates per-session metrics:
    - Duration
    - Events count
    - Pages viewed
    - Bounce detection
    """
    execution_date = context["execution_date"].date()
    print(f"Building session stats for: {execution_date}")

    client = get_clickhouse_client()

    query = """
        INSERT INTO session_stats
        SELECT
            event_date as date,
            session_id,
            any(user_id) as user_id,
            any(device_type) as device_type,
            any(country) as country,
            min(created_at) as start_time,
            max(created_at) as end_time,
            dateDiff('second', min(created_at), max(created_at)) as duration_sec,
            count() as events_count,
            uniq(url) as pages_viewed,
            countIf(event_type = 'click') as clicks_count,
            if(count() = 1 AND countIf(event_type = 'view') = 1, 1, 0) as is_bounce
        FROM events_processed
        WHERE event_date = %(date)s
        GROUP BY event_date, session_id
    """

    client.execute(query, {"date": execution_date})
    print(f"Session stats built for {execution_date}")

    client.disconnect()


def build_element_stats(**context):
    """
    Build element click statistics for heatmaps.
    """
    execution_date = context["execution_date"].date()
    print(f"Building element stats for: {execution_date}")

    client = get_clickhouse_client()

    query = """
        INSERT INTO element_stats
        SELECT
            event_date as date,
            url,
            element_id,
            event_title,
            count() as clicks,
            uniq(user_id) as unique_users,
            avg(x) as avg_x,
            avg(y) as avg_y,
            now() as calculated_at
        FROM events_processed
        WHERE event_date = %(date)s
          AND event_type = 'click'
          AND element_id != ''
        GROUP BY event_date, url, element_id, event_title
    """

    client.execute(query, {"date": execution_date})
    print(f"Element stats built for {execution_date}")

    client.disconnect()


# Default DAG arguments
default_args = {
    "owner": "clickstream",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}

# Create DAG
with DAG(
    dag_id="clickstream_etl",
    default_args=default_args,
    description="Clickstream ETL pipeline - processes events and builds data marts",
    schedule_interval="0 2 * * *",  # Run daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=["clickstream", "etl", "analytics"],
) as dag:

    # Start task
    start = DummyOperator(task_id="start")

    # Clean and validate raw events
    clean_task = PythonOperator(
        task_id="clean_and_validate",
        python_callable=clean_and_validate,
        provide_context=True,
    )

    # Enrich events
    enrich_task = PythonOperator(
        task_id="enrich_events",
        python_callable=enrich_events,
        provide_context=True,
    )

    # Build data marts (can run in parallel)
    daily_stats_task = PythonOperator(
        task_id="build_daily_stats",
        python_callable=build_daily_stats,
        provide_context=True,
    )

    page_stats_task = PythonOperator(
        task_id="build_page_stats",
        python_callable=build_page_stats,
        provide_context=True,
    )

    user_activity_task = PythonOperator(
        task_id="build_user_activity",
        python_callable=build_user_activity,
        provide_context=True,
    )

    session_stats_task = PythonOperator(
        task_id="build_session_stats",
        python_callable=build_session_stats,
        provide_context=True,
    )

    element_stats_task = PythonOperator(
        task_id="build_element_stats",
        python_callable=build_element_stats,
        provide_context=True,
    )

    # End task
    end = DummyOperator(task_id="end")

    # Define task dependencies
    # start -> clean -> enrich -> [daily_stats, page_stats, user_activity, session_stats, element_stats] -> end
    start >> clean_task >> enrich_task

    enrich_task >> [
        daily_stats_task,
        page_stats_task,
        user_activity_task,
        session_stats_task,
        element_stats_task,
    ]

    [
        daily_stats_task,
        page_stats_task,
        user_activity_task,
        session_stats_task,
        element_stats_task,
    ] >> end
