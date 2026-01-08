"""
Event processing service.

Handles validation, enrichment, and storage of clickstream events.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from user_agents import parse as parse_user_agent

from app.models.event import Event, EventBatch, EventError, EventResponse
from app.repositories.clickhouse import clickhouse_repo
from app.repositories.postgres import postgres_repo

logger = logging.getLogger(__name__)


class EventProcessor:
    """Service for processing clickstream events."""

    def __init__(self):
        """Initialize event processor."""
        self._ip_to_country_cache: Dict[str, str] = {}

    async def process_batch(
        self,
        batch: EventBatch,
        source: str = "http",
        client_ip: Optional[str] = None,
    ) -> EventResponse:
        """
        Process a batch of events.

        Args:
            batch: Batch of events to process
            source: Event source (http, kafka, csv)
            client_ip: Client IP address for geolocation

        Returns:
            EventResponse with processing results
        """
        processed = 0
        errors: List[EventError] = []

        # Prepare events for insertion
        raw_events = []
        processed_events = []

        for i, event in enumerate(batch.events):
            try:
                # Enrich and validate event
                raw_event, processed_event = await self._process_event(
                    event, source, client_ip
                )
                raw_events.append(raw_event)
                processed_events.append(processed_event)
                processed += 1
            except Exception as e:
                logger.error(f"Failed to process event {i}: {e}")
                errors.append(EventError(index=i, error=str(e)))

        # Insert events into ClickHouse
        if raw_events:
            try:
                await clickhouse_repo.insert_events_raw(raw_events, source)
            except Exception as e:
                logger.error(f"Failed to insert raw events: {e}")

        if processed_events:
            try:
                await clickhouse_repo.insert_events_processed(processed_events)
            except Exception as e:
                logger.error(f"Failed to insert processed events: {e}")

        status = "ok" if not errors else "partial"
        return EventResponse(status=status, processed=processed, errors=errors)

    async def _process_event(
        self,
        event: Event,
        source: str,
        client_ip: Optional[str],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Process a single event.

        Returns:
            Tuple of (raw_event_dict, processed_event_dict)
        """
        now = datetime.utcnow()
        event_id = int(now.timestamp() * 1000000)

        # Parse User-Agent
        ua_info = self._parse_user_agent(event.user_agent)

        # Parse URL
        url_path = self._extract_url_path(event.url)

        # Get country from IP
        ip = event.ip or client_ip or ""
        country = self._get_country_from_ip(ip)

        # Extract payload data
        payload = event.payload or {}
        payload_dict = payload.model_dump() if hasattr(payload, 'model_dump') else {}

        # Raw event dict
        raw_event = {
            "id": event_id,
            "type": event.type.value,
            "created_at": event.created_at or now,
            "session_id": event.session_id,
            "ip": ip,
            "user_id": event.user_id or 0,
            "url": event.url,
            "referrer": event.referrer or "",
            "device_type": event.device_type.value if event.device_type else ua_info["device_type"],
            "user_agent": event.user_agent or "",
            "payload": payload_dict,
        }

        # Processed event dict - ensure no None values for ClickHouse
        processed_event = {
            "id": event_id,
            "event_type": event.type.value,
            "event_date": (event.created_at or now).date(),
            "event_hour": (event.created_at or now).hour,
            "created_at": event.created_at or now,
            "session_id": event.session_id or "",
            "user_id": event.user_id or 0,
            "url": event.url or "",
            "url_path": url_path or "",
            "referrer": event.referrer or "",
            "device_type": event.device_type.value if event.device_type else (ua_info["device_type"] or "unknown"),
            "country": country or "XX",
            "browser": ua_info["browser"] or "Unknown",
            "browser_version": ua_info["browser_version"] or "",
            "os": ua_info["os"] or "Unknown",
            "os_version": ua_info["os_version"] or "",
            "event_title": payload_dict.get("event_title") or "",
            "element_id": payload_dict.get("element_id") or "",
            "x": int(payload_dict.get("x") or 0),
            "y": int(payload_dict.get("y") or 0),
            "is_bot": 1 if ua_info["is_bot"] else 0,
        }

        # Update session in PostgreSQL
        try:
            await postgres_repo.upsert_session(
                session_id=event.session_id,
                user_id=event.user_id,
                device_type=processed_event["device_type"],
                browser=ua_info["browser"],
                os=ua_info["os"],
                country=country,
                ip_address=ip if ip else None,
            )
        except Exception as e:
            logger.warning(f"Failed to update session: {e}")

        return raw_event, processed_event

    def _parse_user_agent(self, user_agent: Optional[str]) -> Dict[str, Any]:
        """
        Parse User-Agent string to extract device info.

        Returns:
            Dictionary with browser, os, device_type, and is_bot
        """
        if not user_agent:
            return {
                "browser": "Unknown",
                "browser_version": "",
                "os": "Unknown",
                "os_version": "",
                "device_type": "unknown",
                "is_bot": False,
            }

        try:
            ua = parse_user_agent(user_agent)

            # Determine device type
            if ua.is_mobile:
                device_type = "mobile"
            elif ua.is_tablet:
                device_type = "tablet"
            elif ua.is_pc:
                device_type = "desktop"
            else:
                device_type = "unknown"

            return {
                "browser": ua.browser.family or "Unknown",
                "browser_version": ua.browser.version_string or "",
                "os": ua.os.family or "Unknown",
                "os_version": ua.os.version_string or "",
                "device_type": device_type,
                "is_bot": ua.is_bot,
            }
        except Exception as e:
            logger.warning(f"Failed to parse User-Agent: {e}")
            return {
                "browser": "Unknown",
                "browser_version": "",
                "os": "Unknown",
                "os_version": "",
                "device_type": "unknown",
                "is_bot": False,
            }

    def _extract_url_path(self, url: str) -> str:
        """Extract path from URL without query parameters."""
        try:
            parsed = urlparse(url)
            return parsed.path or "/"
        except Exception:
            return url

    def _get_country_from_ip(self, ip: str) -> str:
        """
        Get country code from IP address.

        Uses simple heuristics for demo purposes.
        In production, use GeoIP database.
        """
        if not ip:
            return "XX"

        # Check cache
        if ip in self._ip_to_country_cache:
            return self._ip_to_country_cache[ip]

        # Simple demo logic based on IP ranges
        # In production, use MaxMind GeoIP or similar
        country = "XX"

        if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("127."):
            country = "RU"  # Local IPs -> Russia for demo
        elif ip.startswith("8.8."):
            country = "US"

        self._ip_to_country_cache[ip] = country
        return country

    async def process_single_event(
        self,
        event: Event,
        source: str = "http",
        client_ip: Optional[str] = None,
    ) -> EventResponse:
        """Process a single event (wrapper around batch processing)."""
        batch = EventBatch(events=[event])
        return await self.process_batch(batch, source, client_ip)


# Global service instance
event_processor = EventProcessor()
