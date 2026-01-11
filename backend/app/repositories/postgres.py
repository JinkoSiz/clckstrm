"""
PostgreSQL repository for user and page data.
"""

import logging
from typing import List, Optional

import asyncpg
from asyncpg import Pool

from app.config import settings

logger = logging.getLogger(__name__)


class PostgresRepository:
    """Repository for PostgreSQL operations."""

    def __init__(self):
        """Initialize PostgreSQL repository."""
        self._pool: Optional[Pool] = None

    async def connect(self) -> None:
        """Create connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_database,
                min_size=5,
                max_size=20,
            )
            logger.info("PostgreSQL connection pool created")

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")

    async def health_check(self) -> bool:
        """Check PostgreSQL connection health."""
        try:
            if self._pool is None:
                await self.connect()
            async with self._pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False

    # =========================================================================
    # User operations
    # =========================================================================

    async def get_user_by_external_id(self, external_id: str) -> Optional[dict]:
        """Get user by external ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, external_id, fio, email, country, created_at
                FROM users
                WHERE external_id = $1
                """,
                external_id,
            )
            return dict(row) if row else None

    async def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Get user by internal ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, external_id, fio, email, country, created_at
                FROM users
                WHERE id = $1
                """,
                user_id,
            )
            return dict(row) if row else None

    async def create_user(
        self,
        external_id: str,
        fio: Optional[str] = None,
        email: Optional[str] = None,
        country: Optional[str] = None,
    ) -> dict:
        """Create a new user."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (external_id, fio, email, country)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (external_id) DO UPDATE
                SET fio = COALESCE(EXCLUDED.fio, users.fio),
                    email = COALESCE(EXCLUDED.email, users.email),
                    country = COALESCE(EXCLUDED.country, users.country)
                RETURNING id, external_id, fio, email, country, created_at
                """,
                external_id,
                fio,
                email,
                country,
            )
            return dict(row)

    async def get_users(
        self, limit: int = 100, offset: int = 0
    ) -> List[dict]:
        """Get list of users with pagination."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, external_id, fio, email, country, created_at
                FROM users
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
            return [dict(row) for row in rows]

    async def get_users_count(self) -> int:
        """Get total users count."""
        async with self._pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM users")

    # =========================================================================
    # Page operations
    # =========================================================================

    async def get_page_by_url(self, url: str) -> Optional[dict]:
        """Get page by URL."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, url, title, category, created_at
                FROM pages
                WHERE url = $1
                """,
                url,
            )
            return dict(row) if row else None

    async def create_page(
        self,
        url: str,
        title: Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        """Create or update a page."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO pages (url, title, category)
                VALUES ($1, $2, $3)
                ON CONFLICT (url) DO UPDATE
                SET title = COALESCE(EXCLUDED.title, pages.title),
                    category = COALESCE(EXCLUDED.category, pages.category)
                RETURNING id, url, title, category, created_at
                """,
                url,
                title,
                category,
            )
            return dict(row)

    async def get_pages(
        self,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """Get list of pages with optional category filter."""
        async with self._pool.acquire() as conn:
            if category:
                rows = await conn.fetch(
                    """
                    SELECT id, url, title, category, created_at
                    FROM pages
                    WHERE category = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    category,
                    limit,
                    offset,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, url, title, category, created_at
                    FROM pages
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )
            return [dict(row) for row in rows]

    # =========================================================================
    # Session operations
    # =========================================================================

    async def upsert_session(
        self,
        session_id: str,
        user_id: Optional[int] = None,
        device_type: Optional[str] = None,
        browser: Optional[str] = None,
        os: Optional[str] = None,
        country: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> dict:
        """Create or update a session."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO sessions (
                    session_id, user_id, started_at, device_type,
                    browser, os, country, ip_address
                )
                VALUES ($1, $2, NOW(), $3, $4, $5, $6, $7::inet)
                ON CONFLICT (session_id) DO UPDATE
                SET ended_at = NOW()
                RETURNING id, session_id, user_id, started_at, ended_at,
                          device_type, browser, os, country
                """,
                session_id,
                user_id,
                device_type,
                browser,
                os,
                country,
                ip_address,
            )
            return dict(row)

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, session_id, user_id, started_at, ended_at,
                       device_type, browser, os, country
                FROM sessions
                WHERE session_id = $1
                """,
                session_id,
            )
            return dict(row) if row else None

    async def get_active_sessions_count(self, minutes: int = 30) -> int:
        """Get count of active sessions in last N minutes."""
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM sessions
                WHERE ended_at >= NOW() - INTERVAL '%s minutes'
                   OR (ended_at IS NULL AND started_at >= NOW() - INTERVAL '%s minutes')
                """,
                minutes,
                minutes,
            )


# Global repository instance
postgres_repo = PostgresRepository()
