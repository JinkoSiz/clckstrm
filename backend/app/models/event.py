"""
Event models for Clickstream Analytics.

Defines Pydantic models for event validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    """Type of clickstream event."""

    VIEW = "view"
    CLICK = "click"


class DeviceType(str, Enum):
    """Type of user device."""

    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    UNKNOWN = "unknown"


class EventPayload(BaseModel):
    """
    Custom payload for clickstream event.

    Contains additional event-specific data like element info and coordinates.
    """

    event_title: Optional[str] = Field(
        None,
        description="Custom event title (e.g., 'add_to_cart', 'checkout')",
        max_length=100,
    )
    element_id: Optional[str] = Field(
        None,
        description="CSS selector of clicked element (e.g., '#submit-btn')",
        max_length=255,
    )
    x: Optional[int] = Field(
        None,
        ge=0,
        le=10000,
        description="X coordinate of click",
    )
    y: Optional[int] = Field(
        None,
        ge=0,
        le=10000,
        description="Y coordinate of click",
    )
    extra: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional custom data",
    )


class Event(BaseModel):
    """
    Single clickstream event.

    Represents a user interaction (view or click) on a page.
    """

    type: EventType = Field(
        ...,
        description="Event type: 'view' or 'click'",
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique session identifier",
    )
    user_id: Optional[int] = Field(
        None,
        ge=0,
        description="User identifier (0 for anonymous)",
    )
    url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="Page URL",
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Event creation time (client-side)",
    )
    referrer: Optional[str] = Field(
        None,
        max_length=2048,
        description="Referrer URL",
    )
    device_type: Optional[DeviceType] = Field(
        None,
        description="Device type",
    )
    user_agent: Optional[str] = Field(
        None,
        max_length=1024,
        description="User-Agent string",
    )
    ip: Optional[str] = Field(
        None,
        description="Client IP address",
    )
    country: Optional[str] = Field(
        None,
        max_length=2,
        description="ISO 3166-1 alpha-2 country code",
    )
    payload: Optional[EventPayload] = Field(
        None,
        description="Custom event payload",
    )

    @field_validator("created_at", mode="before")
    @classmethod
    def set_created_at(cls, v: Optional[datetime]) -> datetime:
        """Set default created_at if not provided."""
        return v or datetime.utcnow()

    @field_validator("user_id", mode="before")
    @classmethod
    def set_default_user_id(cls, v: Optional[int]) -> int:
        """Set default user_id to 0 for anonymous users."""
        return v if v is not None else 0

    class Config:
        json_schema_extra = {
            "example": {
                "type": "click",
                "session_id": "sess-abc123",
                "user_id": 1001,
                "url": "/catalog/electronics",
                "created_at": "2025-01-01T10:30:00Z",
                "referrer": "/",
                "device_type": "mobile",
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
                "payload": {
                    "event_title": "add_to_cart",
                    "element_id": "#buy-button",
                    "x": 150,
                    "y": 320,
                },
            }
        }


class EventBatch(BaseModel):
    """
    Batch of clickstream events.

    Used for bulk event ingestion via POST /api/v1/events.
    """

    events: List[Event] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of events to process",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "type": "view",
                        "session_id": "sess-abc123",
                        "user_id": 1001,
                        "url": "/catalog",
                        "created_at": "2025-01-01T10:00:00Z",
                    },
                    {
                        "type": "click",
                        "session_id": "sess-abc123",
                        "user_id": 1001,
                        "url": "/catalog",
                        "created_at": "2025-01-01T10:00:05Z",
                        "payload": {
                            "element_id": "#product-1",
                            "x": 200,
                            "y": 450,
                        },
                    },
                ]
            }
        }


class EventError(BaseModel):
    """Error information for failed event processing."""

    index: int = Field(..., description="Index of failed event in batch")
    error: str = Field(..., description="Error message")


class EventResponse(BaseModel):
    """
    Response for event ingestion request.

    Contains processing status and any errors.
    """

    status: str = Field(
        ...,
        description="Processing status: 'ok' or 'partial'",
    )
    processed: int = Field(
        ...,
        ge=0,
        description="Number of successfully processed events",
    )
    errors: List[EventError] = Field(
        default_factory=list,
        description="List of processing errors",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "processed": 2,
                "errors": [],
            }
        }


class EventFilter(BaseModel):
    """
    Filters for querying events.

    Used in GET /api/v1/events endpoint.
    """

    user_id: Optional[int] = Field(None, description="Filter by user ID")
    session_id: Optional[str] = Field(None, description="Filter by session ID")
    type: Optional[EventType] = Field(None, description="Filter by event type")
    url: Optional[str] = Field(None, description="Filter by URL (partial match)")
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")
    device_type: Optional[DeviceType] = Field(None, description="Filter by device type")
    limit: int = Field(100, ge=1, le=1000, description="Max results to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class EventRecord(BaseModel):
    """
    Event record as stored in database.

    Includes additional fields added during processing.
    """

    id: int
    event_type: str
    created_at: datetime
    received_at: datetime
    session_id: str
    user_id: int
    url: str
    referrer: Optional[str]
    device_type: str
    country: Optional[str]
    browser: Optional[str]
    os: Optional[str]
    event_title: Optional[str]
    element_id: Optional[str]
    x: Optional[int]
    y: Optional[int]

    class Config:
        from_attributes = True
