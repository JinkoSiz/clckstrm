"""
Pytest configuration and fixtures.
"""

import pytest
from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.models.event import Event, EventType, DeviceType, EventPayload


@pytest.fixture
def client() -> Generator:
    """Create test client for FastAPI app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client() -> Generator:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_event() -> Event:
    """Create sample event for testing."""
    return Event(
        type=EventType.CLICK,
        session_id="test-session-123",
        user_id=1001,
        url="/catalog/electronics",
        created_at=datetime.utcnow(),
        referrer="/",
        device_type=DeviceType.DESKTOP,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        ip="192.168.1.1",
        payload=EventPayload(
            event_title="add_to_cart",
            element_id="#buy-button",
            x=150,
            y=320,
        ),
    )


@pytest.fixture
def sample_view_event() -> Event:
    """Create sample view event."""
    return Event(
        type=EventType.VIEW,
        session_id="test-session-456",
        user_id=1002,
        url="/product/1",
        created_at=datetime.utcnow(),
        device_type=DeviceType.MOBILE,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/605.1.15",
    )


@pytest.fixture
def sample_events_batch() -> list:
    """Create batch of sample events."""
    now = datetime.utcnow()
    return [
        {
            "type": "view",
            "session_id": "batch-session-1",
            "user_id": 1001,
            "url": "/",
            "created_at": now.isoformat() + "Z",
        },
        {
            "type": "click",
            "session_id": "batch-session-1",
            "user_id": 1001,
            "url": "/catalog",
            "created_at": now.isoformat() + "Z",
            "payload": {
                "element_id": "#nav-catalog",
                "x": 100,
                "y": 50,
            },
        },
        {
            "type": "view",
            "session_id": "batch-session-2",
            "user_id": 1002,
            "url": "/product/1",
            "created_at": now.isoformat() + "Z",
        },
    ]


@pytest.fixture
def mock_clickhouse():
    """Mock ClickHouse repository."""
    with patch("app.repositories.clickhouse.clickhouse_repo") as mock:
        mock.insert_events_raw = AsyncMock(return_value=3)
        mock.insert_events_processed = AsyncMock(return_value=3)
        mock.get_events = AsyncMock(return_value=([], 0))
        mock.health_check = MagicMock(return_value=True)
        yield mock


@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL repository."""
    with patch("app.repositories.postgres.postgres_repo") as mock:
        mock.connect = AsyncMock()
        mock.close = AsyncMock()
        mock.health_check = AsyncMock(return_value=True)
        mock.upsert_session = AsyncMock(return_value={"session_id": "test"})
        yield mock


@pytest.fixture
def mock_kafka():
    """Mock Kafka consumer."""
    with patch("app.services.kafka_consumer.kafka_consumer") as mock:
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.is_running = False
        yield mock
