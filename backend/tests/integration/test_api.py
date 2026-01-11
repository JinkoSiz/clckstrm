"""
Integration tests for API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


class TestEventsAPI:
    """Tests for /api/v1/events endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_create_events_single(self, client, mock_clickhouse, mock_postgres):
        """Test creating single event via batch endpoint."""
        from app.models.event import EventResponse

        payload = {
            "events": [
                {
                    "type": "view",
                    "session_id": "test-session",
                    "user_id": 1001,
                    "url": "/catalog",
                }
            ]
        }

        mock_response = EventResponse(status="ok", processed=1, errors=[])

        with patch("app.services.event_processor.event_processor.process_batch", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response

            response = client.post("/api/v1/events", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["processed"] == 1

    def test_create_events_batch(self, client, mock_clickhouse, mock_postgres):
        """Test creating batch of events."""
        from app.models.event import EventResponse

        payload = {
            "events": [
                {"type": "view", "session_id": "s1", "url": "/"},
                {"type": "click", "session_id": "s1", "url": "/", "payload": {"element_id": "#btn"}},
                {"type": "view", "session_id": "s2", "url": "/catalog"},
            ]
        }

        mock_response = EventResponse(status="ok", processed=3, errors=[])

        with patch("app.services.event_processor.event_processor.process_batch", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response

            response = client.post("/api/v1/events", json=payload)

        assert response.status_code == 200
        assert response.json()["processed"] == 3

    def test_create_events_validation_error(self, client):
        """Test validation error for invalid events."""
        payload = {
            "events": [
                {"type": "invalid_type", "session_id": "s1", "url": "/"},
            ]
        }

        response = client.post("/api/v1/events", json=payload)

        assert response.status_code == 422

    def test_create_events_empty_batch(self, client):
        """Test empty batch rejection."""
        payload = {"events": []}

        response = client.post("/api/v1/events", json=payload)

        assert response.status_code == 422

    def test_get_events(self, client, mock_clickhouse):
        """Test getting events with filters."""
        mock_clickhouse.get_events.return_value = ([], 0)

        response = client.get("/api/v1/events", params={
            "user_id": 1001,
            "type": "click",
            "limit": 50,
        })

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data

    def test_get_events_pagination(self, client, mock_clickhouse):
        """Test events pagination."""
        mock_clickhouse.get_events.return_value = ([], 100)

        response = client.get("/api/v1/events", params={
            "limit": 10,
            "offset": 20,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 20


class TestStatsAPI:
    """Tests for /api/v1/stats endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_get_overview(self, client, mock_clickhouse):
        """Test getting overview stats."""
        from app.models.stats import OverviewStats

        mock_stats = OverviewStats(
            total_events=10000,
            total_users=1000,
            dau=500,
        )

        with patch("app.api.stats.clickhouse_repo.get_overview_stats", new_callable=AsyncMock) as mock:
            mock.return_value = mock_stats
            response = client.get("/api/v1/stats/overview")

        assert response.status_code == 200

    def test_get_daily_stats(self, client, mock_clickhouse):
        """Test getting daily stats."""
        with patch("app.api.stats.clickhouse_repo.get_daily_stats", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.get("/api/v1/stats/daily", params={
                "from": "2025-01-01",
                "to": "2025-01-07",
            })

        assert response.status_code == 200

    def test_get_page_stats(self, client, mock_clickhouse):
        """Test getting page stats."""
        with patch("app.api.stats.clickhouse_repo.get_page_stats", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.get("/api/v1/stats/pages", params={"limit": 10})

        assert response.status_code == 200

    def test_get_device_stats(self, client, mock_clickhouse):
        """Test getting device stats."""
        with patch("app.api.stats.clickhouse_repo.get_device_stats", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.get("/api/v1/stats/devices")

        assert response.status_code == 200

    def test_get_user_activity(self, client, mock_clickhouse):
        """Test getting user activity (DAU/WAU/MAU)."""
        from app.models.stats import UserActivity
        from datetime import date

        mock_activity = UserActivity(
            date=date.today(),
            dau=1000,
            wau=3000,
            mau=5000,
        )

        with patch("app.api.stats.clickhouse_repo.get_user_activity", new_callable=AsyncMock) as mock:
            mock.return_value = mock_activity
            response = client.get("/api/v1/stats/activity")

        assert response.status_code == 200


class TestHealthAPI:
    """Tests for health check endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_liveness_check(self, client):
        """Test liveness probe."""
        response = client.get("/api/v1/live")

        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    def test_detailed_health_check(self, client, mock_clickhouse, mock_postgres):
        """Test detailed health check."""
        response = client.get("/api/v1/health/detailed")

        # May return 200 or 503 depending on mock setup
        assert response.status_code in [200, 503]
        data = response.json()
        assert "components" in data


class TestRootEndpoint:
    """Tests for root endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data
