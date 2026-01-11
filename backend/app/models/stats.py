"""
Statistics models for Clickstream Analytics.

Defines Pydantic models for analytics data.
"""

from datetime import date as DateType, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DailyStats(BaseModel):
    """Daily aggregated statistics."""

    date: DateType = Field(..., description="Statistics date")
    total_events: int = Field(0, ge=0, description="Total events count")
    total_views: int = Field(0, ge=0, description="Total view events")
    total_clicks: int = Field(0, ge=0, description="Total click events")
    unique_users: int = Field(0, ge=0, description="Unique users count")
    unique_sessions: int = Field(0, ge=0, description="Unique sessions count")
    avg_session_duration_sec: float = Field(
        0.0, ge=0, description="Average session duration in seconds"
    )
    avg_events_per_session: float = Field(
        0.0, ge=0, description="Average events per session"
    )
    bounce_rate: float = Field(
        0.0, ge=0, le=100, description="Bounce rate percentage"
    )

    class Config:
        from_attributes = True


class PageStats(BaseModel):
    """Statistics for a specific page."""

    date: DateType = Field(..., description="Statistics date")
    url: str = Field(..., description="Page URL")
    url_path: Optional[str] = Field(None, description="URL path without query params")
    views: int = Field(0, ge=0, description="View count")
    clicks: int = Field(0, ge=0, description="Click count")
    unique_users: int = Field(0, ge=0, description="Unique users")
    unique_sessions: int = Field(0, ge=0, description="Unique sessions")
    avg_time_on_page_sec: float = Field(
        0.0, ge=0, description="Average time on page in seconds"
    )
    conversion_rate: float = Field(
        0.0, ge=0, le=100, description="Click to view conversion rate"
    )

    class Config:
        from_attributes = True


class DeviceStats(BaseModel):
    """Statistics by device type."""

    date: DateType = Field(..., description="Statistics date")
    device_type: str = Field(..., description="Device type")
    browser: Optional[str] = Field(None, description="Browser name")
    os: Optional[str] = Field(None, description="Operating system")
    events_count: int = Field(0, ge=0, description="Events count")
    unique_users: int = Field(0, ge=0, description="Unique users")
    unique_sessions: int = Field(0, ge=0, description="Unique sessions")
    percentage: float = Field(0.0, ge=0, le=100, description="Percentage of total")

    class Config:
        from_attributes = True


class HourlyStats(BaseModel):
    """Hourly statistics."""

    date: DateType = Field(..., description="Statistics date")
    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    total_events: int = Field(0, ge=0, description="Total events")
    total_views: int = Field(0, ge=0, description="Total views")
    total_clicks: int = Field(0, ge=0, description="Total clicks")
    unique_users: int = Field(0, ge=0, description="Unique users")

    class Config:
        from_attributes = True


class ElementStats(BaseModel):
    """Statistics for clickable elements (for heatmap)."""

    date: DateType = Field(..., description="Statistics date")
    url: str = Field(..., description="Page URL")
    element_id: str = Field(..., description="Element CSS selector")
    event_title: Optional[str] = Field(None, description="Custom event title")
    clicks: int = Field(0, ge=0, description="Click count")
    unique_users: int = Field(0, ge=0, description="Unique users who clicked")
    avg_x: float = Field(0.0, description="Average X coordinate")
    avg_y: float = Field(0.0, description="Average Y coordinate")

    class Config:
        from_attributes = True


class UserActivity(BaseModel):
    """User activity metrics (DAU/WAU/MAU)."""

    date: DateType = Field(..., description="Statistics date")
    dau: int = Field(0, ge=0, description="Daily Active Users")
    wau: int = Field(0, ge=0, description="Weekly Active Users")
    mau: int = Field(0, ge=0, description="Monthly Active Users")
    new_users: int = Field(0, ge=0, description="New users")
    returning_users: int = Field(0, ge=0, description="Returning users")

    class Config:
        from_attributes = True


class SessionStats(BaseModel):
    """Session-level statistics."""

    date: DateType = Field(..., description="Session date")
    session_id: str = Field(..., description="Session ID")
    user_id: int = Field(..., description="User ID")
    device_type: str = Field(..., description="Device type")
    country: Optional[str] = Field(None, description="User country")
    start_time: datetime = Field(..., description="Session start time")
    end_time: datetime = Field(..., description="Session end time")
    duration_sec: int = Field(0, ge=0, description="Session duration in seconds")
    events_count: int = Field(0, ge=0, description="Total events in session")
    pages_viewed: int = Field(0, ge=0, description="Unique pages viewed")
    clicks_count: int = Field(0, ge=0, description="Clicks in session")
    is_bounce: bool = Field(False, description="Is bounce session")

    class Config:
        from_attributes = True


class OverviewStats(BaseModel):
    """Overview statistics for dashboard."""

    # Current period stats
    total_events: int = Field(0, ge=0, description="Total events")
    total_users: int = Field(0, ge=0, description="Total unique users")
    total_sessions: int = Field(0, ge=0, description="Total sessions")
    total_page_views: int = Field(0, ge=0, description="Total page views")
    total_clicks: int = Field(0, ge=0, description="Total clicks")

    # Activity metrics
    dau: int = Field(0, ge=0, description="Daily Active Users")
    wau: int = Field(0, ge=0, description="Weekly Active Users")
    mau: int = Field(0, ge=0, description="Monthly Active Users")

    # Averages
    avg_session_duration_sec: float = Field(
        0.0, ge=0, description="Average session duration"
    )
    avg_pages_per_session: float = Field(
        0.0, ge=0, description="Average pages per session"
    )
    bounce_rate: float = Field(0.0, ge=0, le=100, description="Bounce rate")
    conversion_rate: float = Field(
        0.0, ge=0, le=100, description="Overall click to view ratio"
    )

    # Device breakdown
    device_breakdown: List[DeviceStats] = Field(
        default_factory=list, description="Stats by device type"
    )

    # Top pages
    top_pages: List[PageStats] = Field(
        default_factory=list, description="Top 10 pages by views"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_events": 150000,
                "total_users": 5000,
                "total_sessions": 12000,
                "total_page_views": 100000,
                "total_clicks": 50000,
                "dau": 1200,
                "wau": 3500,
                "mau": 5000,
                "avg_session_duration_sec": 180.5,
                "avg_pages_per_session": 4.2,
                "bounce_rate": 35.5,
                "conversion_rate": 50.0,
                "device_breakdown": [],
                "top_pages": [],
            }
        }


class ConversionStats(BaseModel):
    """Conversion statistics."""

    date: DateType = Field(..., description="Statistics date")
    total_views: int = Field(0, ge=0, description="Total views")
    total_clicks: int = Field(0, ge=0, description="Total clicks")
    conversion_rate: float = Field(
        0.0, ge=0, le=100, description="Conversion rate percentage"
    )

    # Trend compared to previous period
    views_change_pct: float = Field(0.0, description="Views change %")
    clicks_change_pct: float = Field(0.0, description="Clicks change %")
    conversion_change_pct: float = Field(0.0, description="Conversion change %")

    class Config:
        from_attributes = True
