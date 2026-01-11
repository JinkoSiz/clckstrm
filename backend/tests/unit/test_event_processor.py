"""
Unit tests for EventProcessor service.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.event import Event, EventBatch, EventType, DeviceType, EventPayload
from app.services.event_processor import EventProcessor


class TestEventProcessor:
    """Tests for EventProcessor service."""

    @pytest.fixture
    def processor(self):
        """Create EventProcessor instance."""
        return EventProcessor()

    def test_parse_user_agent_chrome_windows(self, processor):
        """Test parsing Chrome on Windows user agent."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        result = processor._parse_user_agent(ua)

        assert result["browser"] == "Chrome"
        assert result["os"] == "Windows"
        assert result["device_type"] == "desktop"
        assert result["is_bot"] is False

    def test_parse_user_agent_safari_iphone(self, processor):
        """Test parsing Safari on iPhone user agent."""
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/605.1.15"
        result = processor._parse_user_agent(ua)

        assert result["browser"] == "Mobile Safari"
        assert result["os"] == "iOS"
        assert result["device_type"] == "mobile"

    def test_parse_user_agent_android(self, processor):
        """Test parsing Android user agent."""
        ua = "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"
        result = processor._parse_user_agent(ua)

        assert result["os"] == "Android"
        assert result["device_type"] == "mobile"

    def test_parse_user_agent_tablet(self, processor):
        """Test parsing iPad user agent."""
        ua = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/605.1.15"
        result = processor._parse_user_agent(ua)

        assert result["device_type"] == "tablet"

    def test_parse_user_agent_empty(self, processor):
        """Test parsing empty user agent."""
        result = processor._parse_user_agent(None)

        assert result["browser"] == "Unknown"
        assert result["os"] == "Unknown"
        assert result["device_type"] == "unknown"

    def test_extract_url_path(self, processor):
        """Test URL path extraction."""
        assert processor._extract_url_path("/catalog?page=1") == "/catalog"
        assert processor._extract_url_path("/product/123") == "/product/123"
        assert processor._extract_url_path("/") == "/"
        assert processor._extract_url_path("/search?q=test&sort=asc") == "/search"

    def test_get_country_from_local_ip(self, processor):
        """Test country detection for local IPs."""
        assert processor._get_country_from_ip("192.168.1.1") == "RU"
        assert processor._get_country_from_ip("10.0.0.1") == "RU"
        assert processor._get_country_from_ip("127.0.0.1") == "RU"

    def test_get_country_from_empty_ip(self, processor):
        """Test country detection for empty IP."""
        assert processor._get_country_from_ip("") == "XX"
        assert processor._get_country_from_ip(None) == "XX"

    @pytest.mark.asyncio
    async def test_process_single_event(self, processor, mock_clickhouse, mock_postgres):
        """Test processing single event."""
        event = Event(
            type=EventType.CLICK,
            session_id="test-session",
            user_id=1001,
            url="/catalog",
        )

        with patch.object(processor, "_process_event") as mock_process:
            mock_process.return_value = (
                {"id": 1, "type": "click"},
                {"id": 1, "event_type": "click"},
            )

            response = await processor.process_single_event(event)

            assert response.status in ["ok", "partial"]

    @pytest.mark.asyncio
    async def test_process_batch(self, processor, mock_clickhouse, mock_postgres):
        """Test processing batch of events."""
        events = [
            Event(type=EventType.VIEW, session_id="s1", url="/"),
            Event(type=EventType.CLICK, session_id="s1", url="/catalog"),
        ]
        batch = EventBatch(events=events)

        with patch.object(processor, "_process_event") as mock_process:
            mock_process.return_value = (
                {"id": 1, "type": "view"},
                {"id": 1, "event_type": "view"},
            )

            response = await processor.process_batch(batch, source="http")

            assert response.processed == 2
            assert len(response.errors) == 0

    @pytest.mark.asyncio
    async def test_process_batch_with_error(self, processor, mock_clickhouse, mock_postgres):
        """Test batch processing with error."""
        events = [
            Event(type=EventType.VIEW, session_id="s1", url="/"),
        ]
        batch = EventBatch(events=events)

        with patch.object(processor, "_process_event") as mock_process:
            mock_process.side_effect = ValueError("Test error")

            response = await processor.process_batch(batch, source="http")

            assert response.processed == 0
            assert len(response.errors) == 1
            assert "Test error" in response.errors[0].error

    @pytest.mark.asyncio
    async def test_process_event_enrichment(self, processor, mock_postgres):
        """Test event enrichment during processing."""
        event = Event(
            type=EventType.CLICK,
            session_id="test-session",
            user_id=1001,
            url="/product/1?ref=home",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            payload=EventPayload(
                event_title="add_to_cart",
                element_id="#buy-btn",
                x=100,
                y=200,
            ),
        )

        raw, processed = await processor._process_event(event, "http", "192.168.1.1")

        # Check raw event
        assert raw["type"] == "click"
        assert raw["session_id"] == "test-session"

        # Check processed event enrichment
        assert processed["url_path"] == "/product/1"
        assert processed["browser"] == "Chrome"
        assert processed["os"] == "Windows"
        assert processed["event_title"] == "add_to_cart"
        assert processed["x"] == 100
