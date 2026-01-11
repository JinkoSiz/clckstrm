"""
ClickHouse repository for event storage and analytics queries.
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError

from app.config import settings
from app.models.event import Event, EventFilter, EventRecord
from app.models.stats import (
    ConversionStats,
    DailyStats,
    DeviceStats,
    ElementStats,
    HourlyStats,
    OverviewStats,
    PageStats,
    UserActivity,
)

logger = logging.getLogger(__name__)


class ClickHouseRepository:
    """Repository for ClickHouse operations."""

    def __init__(self):
        """Initialize ClickHouse client."""
        self._client: Optional[Client] = None

    def _get_client(self) -> Client:
        """Get or create ClickHouse client."""
        if self._client is None:
            self._client = Client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                user=settings.clickhouse_user,
                password=settings.clickhouse_password,
                database=settings.clickhouse_database,
            )
        return self._client

    def close(self) -> None:
        """Close ClickHouse connection."""
        if self._client:
            self._client.disconnect()
            self._client = None

    def health_check(self) -> bool:
        """Check ClickHouse connection health."""
        try:
            client = self._get_client()
            result = client.execute("SELECT 1")
            return result == [(1,)]
        except ClickHouseError as e:
            logger.error(f"ClickHouse health check failed: {e}")
            return False

    async def insert_events_raw(
        self, events: List[Dict[str, Any]], source: str = "http"
    ) -> int:
        """
        Insert raw events into events_raw table.

        Args:
            events: List of event dictionaries
            source: Event source (http, kafka, csv)

        Returns:
            Number of inserted events
        """
        if not events:
            return 0

        client = self._get_client()
        now = datetime.utcnow()

        rows = []
        for i, event in enumerate(events):
            payload = event.get("payload", {})
            if isinstance(payload, dict):
                payload = json.dumps(payload)

            rows.append({
                "id": int(now.timestamp() * 1000000) + i,
                "event_type": event.get("type", "view"),
                "created_at": event.get("created_at", now),
                "received_at": now,
                "session_id": event.get("session_id", ""),
                "ip": event.get("ip", ""),
                "user_id": event.get("user_id", 0),
                "url": event.get("url", ""),
                "referrer": event.get("referrer", ""),
                "device_type": event.get("device_type", "unknown"),
                "user_agent": event.get("user_agent", ""),
                "payload": payload,
                "source": source,
                "country": event.get("country", ""),
            })

        try:
            client.execute(
                """
                INSERT INTO events_raw (
                    id, event_type, created_at, received_at, session_id,
                    ip, user_id, url, referrer, device_type, user_agent,
                    payload, source, country
                ) VALUES
                """,
                rows,
            )
            logger.info(f"Inserted {len(rows)} events into events_raw")
            return len(rows)
        except ClickHouseError as e:
            logger.error(f"Failed to insert events: {e}")
            raise

    async def insert_events_processed(
        self, events: List[Dict[str, Any]]
    ) -> int:
        """
        Insert processed events into events_processed table.

        Args:
            events: List of processed event dictionaries

        Returns:
            Number of inserted events
        """
        if not events:
            return 0

        client = self._get_client()

        try:
            client.execute(
                """
                INSERT INTO events_processed (
                    id, event_type, event_date, event_hour, created_at,
                    session_id, user_id, url, url_path, referrer,
                    device_type, country, browser, browser_version,
                    os, os_version, event_title, element_id, x, y, is_bot
                ) VALUES
                """,
                events,
            )
            return len(events)
        except ClickHouseError as e:
            logger.error(f"Failed to insert processed events: {e}")
            raise

    async def get_events(
        self, filter: EventFilter
    ) -> Tuple[List[EventRecord], int]:
        """
        Get events with filtering and pagination.

        Args:
            filter: Event filter parameters

        Returns:
            Tuple of (events list, total count)
        """
        client = self._get_client()

        # Build WHERE clause
        conditions = []
        params = {}

        if filter.user_id is not None:
            conditions.append("user_id = {user_id:UInt64}")
            params["user_id"] = filter.user_id

        if filter.session_id:
            conditions.append("session_id = {session_id:String}")
            params["session_id"] = filter.session_id

        if filter.type:
            conditions.append("event_type = {event_type:String}")
            params["event_type"] = filter.type.value

        if filter.url:
            conditions.append("url LIKE {url:String}")
            params["url"] = f"%{filter.url}%"

        if filter.date_from:
            conditions.append("created_at >= {date_from:DateTime}")
            params["date_from"] = filter.date_from

        if filter.date_to:
            conditions.append("created_at <= {date_to:DateTime}")
            params["date_to"] = filter.date_to

        if filter.device_type:
            conditions.append("device_type = {device_type:String}")
            params["device_type"] = filter.device_type.value

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_query = f"""
            SELECT count() FROM events_processed
            WHERE {where_clause}
        """
        total = client.execute(count_query, params, settings={'use_client_time_zone': True})[0][0]

        # Get events with pagination
        query = f"""
            SELECT
                id, event_type, created_at, created_at as received_at,
                session_id, user_id, url, referrer, device_type,
                country, browser, os, event_title, element_id, x, y
            FROM events_processed
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT {filter.limit} OFFSET {filter.offset}
        """

        rows = client.execute(query, params, settings={'use_client_time_zone': True})

        events = [
            EventRecord(
                id=row[0],
                event_type=row[1],
                created_at=row[2],
                received_at=row[3],
                session_id=row[4],
                user_id=row[5] if row[5] else None,
                url=row[6],
                referrer=row[7] if row[7] else None,
                device_type=row[8] if row[8] else None,
                country=row[9] if row[9] else None,
                browser=row[10] if row[10] else None,
                os=row[11] if row[11] else None,
                event_title=row[12] if row[12] else None,
                element_id=row[13] if row[13] else None,
                x=row[14] if row[14] else None,
                y=row[15] if row[15] else None,
            )
            for row in rows
        ]

        return events, total

    async def get_daily_stats(
        self, date_from: date, date_to: date
    ) -> List[DailyStats]:
        """Get daily statistics for date range."""
        client = self._get_client()

        query = """
            SELECT
                event_date as date,
                count() as total_events,
                countIf(event_type = 'view') as total_views,
                countIf(event_type = 'click') as total_clicks,
                uniq(user_id) as unique_users,
                uniq(session_id) as unique_sessions,
                0 as avg_session_duration_sec,
                count() / uniq(session_id) as avg_events_per_session,
                0 as bounce_rate
            FROM events_processed
            WHERE event_date >= {date_from:Date} AND event_date <= {date_to:Date}
            GROUP BY event_date
            ORDER BY event_date
        """

        rows = client.execute(
            query,
            {"date_from": date_from, "date_to": date_to},
            settings={'use_client_time_zone': True}
        )

        return [
            DailyStats(
                date=row[0],
                total_events=row[1],
                total_views=row[2],
                total_clicks=row[3],
                unique_users=row[4],
                unique_sessions=row[5],
                avg_session_duration_sec=row[6],
                avg_events_per_session=row[7],
                bounce_rate=row[8],
            )
            for row in rows
        ]

    async def get_page_stats(
        self, date_from: date, date_to: date, limit: int = 10
    ) -> List[PageStats]:
        """Get page statistics for date range."""
        client = self._get_client()

        query = f"""
            SELECT
                event_date as date,
                url,
                url_path,
                countIf(event_type = 'view') as views,
                countIf(event_type = 'click') as clicks,
                uniq(user_id) as unique_users,
                uniq(session_id) as unique_sessions,
                0 as avg_time_on_page_sec,
                if(views > 0, clicks * 100.0 / views, 0) as conversion_rate
            FROM events_processed
            WHERE event_date >= {{date_from:Date}} AND event_date <= {{date_to:Date}}
            GROUP BY event_date, url, url_path
            ORDER BY views DESC
            LIMIT {limit}
        """

        rows = client.execute(
            query,
            {"date_from": date_from, "date_to": date_to},
            settings={'use_client_time_zone': True}
        )

        return [
            PageStats(
                date=row[0],
                url=row[1],
                url_path=row[2],
                views=row[3],
                clicks=row[4],
                unique_users=row[5],
                unique_sessions=row[6],
                avg_time_on_page_sec=row[7],
                conversion_rate=row[8],
            )
            for row in rows
        ]

    async def get_device_stats(
        self, date_from: date, date_to: date
    ) -> List[DeviceStats]:
        """Get device statistics for date range."""
        client = self._get_client()

        query = """
            SELECT
                event_date as date,
                device_type,
                browser,
                os,
                count() as events_count,
                uniq(user_id) as unique_users,
                uniq(session_id) as unique_sessions
            FROM events_processed
            WHERE event_date >= {date_from:Date} AND event_date <= {date_to:Date}
            GROUP BY event_date, device_type, browser, os
            ORDER BY events_count DESC
        """

        rows = client.execute(
            query,
            {"date_from": date_from, "date_to": date_to},
            settings={'use_client_time_zone': True}
        )

        # Calculate percentages
        total_events = sum(row[4] for row in rows)

        return [
            DeviceStats(
                date=row[0],
                device_type=row[1],
                browser=row[2],
                os=row[3],
                events_count=row[4],
                unique_users=row[5],
                unique_sessions=row[6],
                percentage=round(row[4] * 100.0 / total_events, 2) if total_events > 0 else 0,
            )
            for row in rows
        ]

    async def get_user_activity(
        self, target_date: date
    ) -> UserActivity:
        """Get DAU/WAU/MAU for a specific date."""
        client = self._get_client()

        from datetime import timedelta
        week_start = target_date - timedelta(days=7)
        month_start = target_date - timedelta(days=30)

        query = """
            SELECT
                {target_date:Date} as date,
                uniq(user_id) as dau,
                uniqIf(user_id, event_date >= {week_start:Date}) as wau,
                uniqIf(user_id, event_date >= {month_start:Date}) as mau
            FROM events_processed
            WHERE event_date >= {month_start:Date} AND event_date <= {target_date:Date}
        """

        rows = client.execute(
            query,
            {
                "target_date": target_date,
                "week_start": week_start,
                "month_start": month_start,
            },
            settings={'use_client_time_zone': True}
        )

        if rows:
            row = rows[0]
            return UserActivity(
                date=target_date,
                dau=row[1],
                wau=row[2],
                mau=row[3],
                new_users=0,
                returning_users=0,
            )

        return UserActivity(date=target_date)

    async def get_overview_stats(
        self, date_from: date, date_to: date
    ) -> OverviewStats:
        """Get overview statistics for dashboard."""
        client = self._get_client()

        # Get main stats
        main_query = """
            SELECT
                count() as total_events,
                uniq(user_id) as total_users,
                uniq(session_id) as total_sessions,
                countIf(event_type = 'view') as total_views,
                countIf(event_type = 'click') as total_clicks
            FROM events_processed
            WHERE event_date >= {date_from:Date} AND event_date <= {date_to:Date}
        """

        main_rows = client.execute(
            main_query,
            {"date_from": date_from, "date_to": date_to},
            settings={'use_client_time_zone': True}
        )

        if not main_rows:
            return OverviewStats()

        row = main_rows[0]

        # Get device breakdown
        device_stats = await self.get_device_stats(date_from, date_to)

        # Get top pages
        page_stats = await self.get_page_stats(date_from, date_to, limit=10)

        # Get user activity for latest date
        user_activity = await self.get_user_activity(date_to)

        total_views = row[3]
        total_clicks = row[4]

        return OverviewStats(
            total_events=row[0],
            total_users=row[1],
            total_sessions=row[2],
            total_page_views=total_views,
            total_clicks=total_clicks,
            dau=user_activity.dau,
            wau=user_activity.wau,
            mau=user_activity.mau,
            avg_session_duration_sec=0.0,
            avg_pages_per_session=round(total_views / row[2], 2) if row[2] > 0 else 0,
            bounce_rate=0.0,
            conversion_rate=round(total_clicks * 100.0 / total_views, 2) if total_views > 0 else 0,
            device_breakdown=device_stats[:5],
            top_pages=page_stats[:10],
        )

    async def get_element_stats(
        self, url: str, date_from: date, date_to: date
    ) -> List[ElementStats]:
        """Get element click statistics for heatmap."""
        client = self._get_client()

        query = """
            SELECT
                event_date as date,
                url,
                element_id,
                event_title,
                count() as clicks,
                uniq(user_id) as unique_users,
                avg(x) as avg_x,
                avg(y) as avg_y
            FROM events_processed
            WHERE url = {url:String}
                AND event_date >= {date_from:Date}
                AND event_date <= {date_to:Date}
                AND event_type = 'click'
                AND element_id != ''
            GROUP BY event_date, url, element_id, event_title
            ORDER BY clicks DESC
        """

        rows = client.execute(
            query,
            {"url": url, "date_from": date_from, "date_to": date_to},
            settings={'use_client_time_zone': True}
        )

        return [
            ElementStats(
                date=row[0],
                url=row[1],
                element_id=row[2],
                event_title=row[3],
                clicks=row[4],
                unique_users=row[5],
                avg_x=row[6],
                avg_y=row[7],
            )
            for row in rows
        ]


# Global repository instance
clickhouse_repo = ClickHouseRepository()
