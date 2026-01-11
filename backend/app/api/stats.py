"""
Statistics API endpoints.

Provides analytics data for dashboards.
"""

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Query

from app.models.stats import (
    DailyStats,
    DeviceStats,
    ElementStats,
    OverviewStats,
    PageStats,
    UserActivity,
)
from app.repositories.clickhouse import clickhouse_repo

router = APIRouter()


@router.get(
    "/overview",
    response_model=OverviewStats,
    summary="Get overview statistics",
    description="Get aggregated statistics for the dashboard overview.",
)
async def get_overview(
    date_from: Optional[date] = Query(
        None,
        alias="from",
        description="Start date (default: 30 days ago)",
    ),
    date_to: Optional[date] = Query(
        None,
        alias="to",
        description="End date (default: today)",
    ),
) -> OverviewStats:
    """
    Get overview statistics for the dashboard.
    """
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=30)

    return await clickhouse_repo.get_overview_stats(date_from, date_to)


@router.get(
    "/daily",
    response_model=List[DailyStats],
    summary="Get daily statistics",
    description="Get daily aggregated statistics for a date range.",
)
async def get_daily_stats(
    date_from: Optional[date] = Query(
        None,
        alias="from",
        description="Start date (default: 7 days ago)",
    ),
    date_to: Optional[date] = Query(
        None,
        alias="to",
        description="End date (default: today)",
    ),
) -> List[DailyStats]:
    """
    Get daily statistics for charting.
    """
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=7)

    return await clickhouse_repo.get_daily_stats(date_from, date_to)


@router.get(
    "/pages",
    response_model=List[PageStats],
    summary="Get page statistics",
    description="Get statistics for individual pages.",
)
async def get_page_stats(
    date_from: Optional[date] = Query(
        None,
        alias="from",
        description="Start date (default: 7 days ago)",
    ),
    date_to: Optional[date] = Query(
        None,
        alias="to",
        description="End date (default: today)",
    ),
    limit: int = Query(10, ge=1, le=100, description="Max pages to return"),
) -> List[PageStats]:
    """
    Get statistics for top pages.
    """
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=7)

    return await clickhouse_repo.get_page_stats(date_from, date_to, limit)


@router.get(
    "/devices",
    response_model=List[DeviceStats],
    summary="Get device statistics",
    description="Get statistics broken down by device type.",
)
async def get_device_stats(
    date_from: Optional[date] = Query(
        None,
        alias="from",
        description="Start date (default: 7 days ago)",
    ),
    date_to: Optional[date] = Query(
        None,
        alias="to",
        description="End date (default: today)",
    ),
) -> List[DeviceStats]:
    """
    Get statistics by device type.
    """
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=7)

    return await clickhouse_repo.get_device_stats(date_from, date_to)


@router.get(
    "/activity",
    response_model=UserActivity,
    summary="Get user activity metrics",
    description="Get DAU/WAU/MAU metrics for a specific date.",
)
async def get_user_activity(
    target_date: Optional[date] = Query(
        None,
        alias="date",
        description="Target date (default: today)",
    ),
) -> UserActivity:
    """
    Get user activity metrics (DAU/WAU/MAU).
    """
    if target_date is None:
        target_date = date.today()

    return await clickhouse_repo.get_user_activity(target_date)


@router.get(
    "/elements",
    response_model=List[ElementStats],
    summary="Get element statistics",
    description="Get click statistics for page elements (for heatmap).",
)
async def get_element_stats(
    url: str = Query(..., description="Page URL to analyze"),
    date_from: Optional[date] = Query(
        None,
        alias="from",
        description="Start date (default: 7 days ago)",
    ),
    date_to: Optional[date] = Query(
        None,
        alias="to",
        description="End date (default: today)",
    ),
) -> List[ElementStats]:
    """
    Get click statistics for page elements.
    """
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=7)

    return await clickhouse_repo.get_element_stats(url, date_from, date_to)


@router.get(
    "/conversion",
    response_model=dict,
    summary="Get conversion statistics",
    description="Get click-to-view conversion rate.",
)
async def get_conversion_stats(
    date_from: Optional[date] = Query(
        None,
        alias="from",
        description="Start date (default: 7 days ago)",
    ),
    date_to: Optional[date] = Query(
        None,
        alias="to",
        description="End date (default: today)",
    ),
) -> dict:
    """
    Get conversion statistics.
    """
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=7)

    daily_stats = await clickhouse_repo.get_daily_stats(date_from, date_to)

    total_views = sum(s.total_views for s in daily_stats)
    total_clicks = sum(s.total_clicks for s in daily_stats)
    conversion_rate = (total_clicks / total_views * 100) if total_views > 0 else 0

    return {
        "date_from": str(date_from),
        "date_to": str(date_to),
        "total_views": total_views,
        "total_clicks": total_clicks,
        "conversion_rate": round(conversion_rate, 2),
    }
