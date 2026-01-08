"""
Kafka consumer service for processing clickstream events.
"""

import asyncio
import json
import logging
from typing import Optional

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from app.config import settings
from app.models.event import Event, EventBatch
from app.services.event_processor import event_processor
from app.metrics.prometheus import record_event_processed, record_kafka_consumed

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    """Service for consuming events from Kafka."""

    def __init__(self):
        """Initialize Kafka consumer service."""
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the Kafka consumer."""
        if self._running:
            logger.warning("Kafka consumer already running")
            return

        try:
            self._consumer = AIOKafkaConsumer(
                settings.kafka_topic,
                bootstrap_servers=settings.kafka_servers_list,
                group_id=settings.kafka_group_id,
                auto_offset_reset=settings.kafka_auto_offset_reset,
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )

            await self._consumer.start()
            self._running = True
            logger.info(
                f"Kafka consumer started, subscribed to topic: {settings.kafka_topic}"
            )

            # Start consuming in background
            self._task = asyncio.create_task(self._consume_loop())

        except KafkaError as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
            logger.info("Kafka consumer stopped")

    async def _consume_loop(self) -> None:
        """Main consumption loop."""
        batch: list = []
        batch_timeout = settings.batch_timeout_ms / 1000.0
        last_batch_time = asyncio.get_event_loop().time()

        try:
            async for message in self._consumer:
                if not self._running:
                    break

                try:
                    # Parse event from message
                    event_data = message.value
                    event = self._parse_event(event_data)

                    if event:
                        batch.append(event)

                    # Check if batch is ready
                    current_time = asyncio.get_event_loop().time()
                    batch_age = current_time - last_batch_time

                    if len(batch) >= settings.batch_size or batch_age >= batch_timeout:
                        if batch:
                            await self._process_batch(batch)
                            batch = []
                            last_batch_time = current_time

                except Exception as e:
                    logger.error(f"Error processing Kafka message: {e}")

        except asyncio.CancelledError:
            # Process remaining batch before stopping
            if batch:
                await self._process_batch(batch)
            raise

    def _parse_event(self, data: dict) -> Optional[Event]:
        """Parse event from Kafka message data."""
        try:
            # Handle payload as JSON string from generator
            if "payload" in data and isinstance(data["payload"], str):
                try:
                    data["payload"] = json.loads(data["payload"])
                except json.JSONDecodeError:
                    data["payload"] = None

            # Remove extra fields that aren't part of Event model
            event_fields = {"type", "session_id", "user_id", "url", "created_at",
                          "referrer", "device_type", "user_agent", "ip", "payload", "country"}
            filtered_data = {k: v for k, v in data.items() if k in event_fields}

            return Event(**filtered_data)
        except Exception as e:
            logger.warning(f"Failed to parse event: {e}, data: {data}")
            return None

    async def _process_batch(self, events: list) -> None:
        """Process a batch of events."""
        if not events:
            return

        try:
            batch = EventBatch(events=events)
            response = await event_processor.process_batch(batch, source="kafka")

            # Record metrics
            record_kafka_consumed(settings.kafka_topic, len(events))
            for event in events:
                record_event_processed("kafka", event.type.value if hasattr(event.type, 'value') else str(event.type))

            logger.info(
                f"Processed Kafka batch: {response.processed} events, "
                f"{len(response.errors)} errors"
            )
        except Exception as e:
            logger.error(f"Failed to process Kafka batch: {e}")

    @property
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._running


# Global service instance
kafka_consumer = KafkaConsumerService()
