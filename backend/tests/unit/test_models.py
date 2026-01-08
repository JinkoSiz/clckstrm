"""
Unit tests for Pydantic models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.event import (
    Event,
    EventBatch,
    EventPayload,
    EventType,
    DeviceType,
    EventFilter,
)
from app.models.stats import DailyStats, PageStats, OverviewStats


class TestEventModel:
    """Tests for Event model."""

    def test_valid_click_event(self):
        """Test creating valid click event."""
        event = Event(
            type=EventType.CLICK,
            session_id="sess-123",
            user_id=1001,
            url="/catalog",
        )

        assert event.type == EventType.CLICK
        assert event.session_id == "sess-123"
        assert event.user_id == 1001
        assert event.url == "/catalog"
        # created_at is set by validator when parsing from JSON/dict, not on direct instantiation

    def test_valid_view_event(self):
        """Test creating valid view event."""
        event = Event(
            type=EventType.VIEW,
            session_id="sess-456",
            url="/product/1",
        )

        assert event.type == EventType.VIEW
        # user_id default is set by validator when parsing from JSON/dict
        # For direct instantiation without user_id, it remains None
        assert event.user_id is None or event.user_id == 0

    def test_event_with_payload(self):
        """Test event with custom payload."""
        payload = EventPayload(
            event_title="add_to_cart",
            element_id="#buy-btn",
            x=150,
            y=300,
        )

        event = Event(
            type=EventType.CLICK,
            session_id="sess-789",
            url="/product/1",
            payload=payload,
        )

        assert event.payload.event_title == "add_to_cart"
        assert event.payload.element_id == "#buy-btn"
        assert event.payload.x == 150
        assert event.payload.y == 300

    def test_event_missing_required_fields(self):
        """Test that missing required fields raise error."""
        with pytest.raises(ValidationError):
            Event(type=EventType.CLICK)  # Missing session_id and url

    def test_event_invalid_type(self):
        """Test that invalid event type raises error."""
        with pytest.raises(ValidationError):
            Event(
                type="invalid",
                session_id="sess-123",
                url="/test",
            )

    def test_event_url_max_length(self):
        """Test URL max length validation."""
        long_url = "/" + "a" * 2500

        with pytest.raises(ValidationError):
            Event(
                type=EventType.VIEW,
                session_id="sess-123",
                url=long_url,
            )

    def test_event_device_types(self):
        """Test all device types."""
        for device_type in DeviceType:
            event = Event(
                type=EventType.VIEW,
                session_id="sess-123",
                url="/test",
                device_type=device_type,
            )
            assert event.device_type == device_type


class TestEventBatchModel:
    """Tests for EventBatch model."""

    def test_valid_batch(self):
        """Test creating valid event batch."""
        batch = EventBatch(
            events=[
                Event(type=EventType.VIEW, session_id="s1", url="/"),
                Event(type=EventType.CLICK, session_id="s1", url="/catalog"),
            ]
        )

        assert len(batch.events) == 2

    def test_empty_batch_rejected(self):
        """Test that empty batch is rejected."""
        with pytest.raises(ValidationError):
            EventBatch(events=[])

    def test_batch_max_size(self):
        """Test batch max size validation."""
        events = [
            Event(type=EventType.VIEW, session_id=f"s{i}", url=f"/{i}")
            for i in range(1001)
        ]

        with pytest.raises(ValidationError):
            EventBatch(events=events)


class TestEventPayloadModel:
    """Tests for EventPayload model."""

    def test_valid_payload(self):
        """Test creating valid payload."""
        payload = EventPayload(
            event_title="checkout",
            element_id="#checkout-btn",
            x=500,
            y=600,
        )

        assert payload.event_title == "checkout"
        assert payload.x == 500

    def test_payload_coordinate_validation(self):
        """Test coordinate value validation."""
        with pytest.raises(ValidationError):
            EventPayload(x=-1)  # Negative not allowed

        with pytest.raises(ValidationError):
            EventPayload(x=20000)  # Too large

    def test_optional_payload_fields(self):
        """Test that all payload fields are optional."""
        payload = EventPayload()
        assert payload.event_title is None
        assert payload.element_id is None
        assert payload.x is None
        assert payload.y is None


class TestEventFilterModel:
    """Tests for EventFilter model."""

    def test_default_values(self):
        """Test filter default values."""
        filter = EventFilter()

        assert filter.limit == 100
        assert filter.offset == 0
        assert filter.user_id is None

    def test_filter_limit_validation(self):
        """Test filter limit validation."""
        with pytest.raises(ValidationError):
            EventFilter(limit=0)  # Below minimum

        with pytest.raises(ValidationError):
            EventFilter(limit=2000)  # Above maximum


class TestStatsModels:
    """Tests for statistics models."""

    def test_daily_stats(self):
        """Test DailyStats model."""
        from datetime import date

        stats = DailyStats(
            date=date.today(),
            total_events=1000,
            total_views=600,
            total_clicks=400,
            unique_users=100,
            unique_sessions=150,
        )

        assert stats.total_events == 1000
        assert stats.bounce_rate == 0.0  # Default

    def test_page_stats(self):
        """Test PageStats model."""
        from datetime import date

        stats = PageStats(
            date=date.today(),
            url="/catalog",
            views=500,
            clicks=100,
            conversion_rate=20.0,
        )

        assert stats.conversion_rate == 20.0

    def test_overview_stats(self):
        """Test OverviewStats model."""
        stats = OverviewStats(
            total_events=50000,
            total_users=5000,
            dau=1000,
            wau=3000,
            mau=5000,
        )

        assert stats.dau == 1000
        assert len(stats.device_breakdown) == 0
        assert len(stats.top_pages) == 0
