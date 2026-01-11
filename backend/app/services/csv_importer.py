"""
CSV import service for bulk event loading.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional

from app.models.event import DeviceType, Event, EventBatch, EventPayload, EventType
from app.services.event_processor import event_processor

logger = logging.getLogger(__name__)


class CSVImporter:
    """Service for importing events from CSV files."""

    def __init__(self, batch_size: int = 1000):
        """
        Initialize CSV importer.

        Args:
            batch_size: Number of events to process in each batch
        """
        self.batch_size = batch_size

    async def import_file(self, file_path: str) -> dict:
        """
        Import events from a CSV file.

        Args:
            file_path: Path to the CSV file

        Returns:
            Dictionary with import statistics
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.suffix.lower() == ".csv":
            raise ValueError(f"Invalid file format: {path.suffix}")

        total_processed = 0
        total_errors = 0
        batches_processed = 0

        logger.info(f"Starting CSV import from: {file_path}")

        for batch in self._read_batches(path):
            try:
                event_batch = EventBatch(events=batch)
                response = await event_processor.process_batch(
                    event_batch, source="csv"
                )
                total_processed += response.processed
                total_errors += len(response.errors)
                batches_processed += 1

                if batches_processed % 10 == 0:
                    logger.info(
                        f"Progress: {total_processed} events processed, "
                        f"{total_errors} errors"
                    )

            except Exception as e:
                logger.error(f"Failed to process batch: {e}")
                total_errors += len(batch)

        logger.info(
            f"CSV import complete: {total_processed} processed, "
            f"{total_errors} errors"
        )

        return {
            "file": str(file_path),
            "total_processed": total_processed,
            "total_errors": total_errors,
            "batches_processed": batches_processed,
        }

    def _read_batches(self, path: Path) -> Generator[List[Event], None, None]:
        """
        Read CSV file in batches.

        Yields:
            Lists of Event objects
        """
        batch: List[Event] = []

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    event = self._parse_row(row)
                    if event:
                        batch.append(event)

                    if len(batch) >= self.batch_size:
                        yield batch
                        batch = []

                except Exception as e:
                    logger.warning(f"Failed to parse row: {e}")

        # Yield remaining events
        if batch:
            yield batch

    def _parse_row(self, row: dict) -> Optional[Event]:
        """
        Parse a CSV row into an Event.

        Expected CSV columns:
        - type: view/click
        - session_id: session identifier
        - user_id: user identifier (optional)
        - url: page URL
        - created_at: timestamp (ISO format or Unix timestamp)
        - referrer: referrer URL (optional)
        - device_type: desktop/mobile/tablet (optional)
        - user_agent: User-Agent string (optional)
        - ip: IP address (optional)
        - event_title: custom event title (optional)
        - element_id: clicked element ID (optional)
        - x: click X coordinate (optional)
        - y: click Y coordinate (optional)
        """
        # Required fields
        event_type = row.get("type", "view").lower()
        session_id = row.get("session_id", "")
        url = row.get("url", "")

        if not session_id or not url:
            return None

        # Parse event type
        try:
            event_type_enum = EventType(event_type)
        except ValueError:
            event_type_enum = EventType.VIEW

        # Parse timestamp
        created_at = self._parse_timestamp(row.get("created_at"))

        # Parse user_id
        user_id = None
        if row.get("user_id"):
            try:
                user_id = int(row["user_id"])
            except ValueError:
                pass

        # Parse device type
        device_type = None
        if row.get("device_type"):
            try:
                device_type = DeviceType(row["device_type"].lower())
            except ValueError:
                pass

        # Parse payload
        payload = None
        if any(row.get(k) for k in ["event_title", "element_id", "x", "y"]):
            payload = EventPayload(
                event_title=row.get("event_title"),
                element_id=row.get("element_id"),
                x=self._parse_int(row.get("x")),
                y=self._parse_int(row.get("y")),
            )

        return Event(
            type=event_type_enum,
            session_id=session_id,
            user_id=user_id,
            url=url,
            created_at=created_at,
            referrer=row.get("referrer"),
            device_type=device_type,
            user_agent=row.get("user_agent"),
            ip=row.get("ip"),
            payload=payload,
        )

    def _parse_timestamp(self, value: Optional[str]) -> Optional[datetime]:
        """Parse timestamp from string."""
        if not value:
            return None

        # Try ISO format
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass

        # Try Unix timestamp
        try:
            return datetime.fromtimestamp(float(value))
        except ValueError:
            pass

        return None

    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Parse integer from string."""
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None


# Global service instance
csv_importer = CSVImporter()
