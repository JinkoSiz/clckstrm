"""
Events API endpoints.

Handles event ingestion and retrieval.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import JSONResponse

from app.models.event import (
    DeviceType,
    Event,
    EventBatch,
    EventFilter,
    EventRecord,
    EventResponse,
    EventType,
)
from app.repositories.clickhouse import clickhouse_repo
from app.services.event_processor import event_processor
from app.services.csv_importer import csv_importer
from app.metrics.prometheus import record_event_processed, record_event_error

router = APIRouter()


@router.post(
    "",
    response_model=EventResponse,
    summary="Ingest events",
    description="Receive and process a batch of clickstream events.",
)
async def create_events(
    batch: EventBatch,
    request: Request,
) -> EventResponse:
    """
    Ingest a batch of clickstream events.

    - Validates and enriches each event
    - Stores events in ClickHouse
    - Returns processing results

    Accepts up to 1000 events per request.
    """
    # Get client IP for geolocation
    client_ip = request.client.host if request.client else None

    # Process events
    response = await event_processor.process_batch(
        batch,
        source="http",
        client_ip=client_ip,
    )

    # Record metrics
    for event in batch.events:
        record_event_processed("http", event.type.value)

    for error in response.errors:
        record_event_error("http", "validation")

    return response


@router.get(
    "",
    response_model=dict,
    summary="Get events",
    description="Retrieve events with filtering and pagination.",
)
async def get_events(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    type: Optional[EventType] = Query(None, description="Filter by event type"),
    url: Optional[str] = Query(None, description="Filter by URL (partial match)"),
    date_from: Optional[datetime] = Query(None, alias="from", description="Start date"),
    date_to: Optional[datetime] = Query(None, alias="to", description="End date"),
    device_type: Optional[DeviceType] = Query(None, description="Filter by device type"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> dict:
    """
    Get events with optional filtering.

    Supports filtering by:
    - user_id: specific user
    - session_id: specific session
    - type: view or click
    - url: partial URL match
    - from/to: date range
    - device_type: desktop, mobile, tablet

    Returns paginated results with total count.
    """
    filter_params = EventFilter(
        user_id=user_id,
        session_id=session_id,
        type=type,
        url=url,
        date_from=date_from,
        date_to=date_to,
        device_type=device_type,
        limit=limit,
        offset=offset,
    )

    events, total = await clickhouse_repo.get_events(filter_params)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": [e.model_dump() for e in events],
    }


@router.post(
    "/import",
    response_model=dict,
    summary="Import events from CSV",
    description="Import events from an uploaded CSV file.",
)
async def import_csv(
    file: UploadFile = File(..., description="CSV file with events"),
) -> dict:
    """
    Import events from a CSV file.

    Expected CSV columns:
    - type: view/click (required)
    - session_id: session identifier (required)
    - url: page URL (required)
    - user_id: user identifier (optional)
    - created_at: timestamp (optional)
    - referrer: referrer URL (optional)
    - device_type: desktop/mobile/tablet (optional)
    - user_agent: User-Agent string (optional)
    - ip: IP address (optional)
    - event_title: custom event title (optional)
    - element_id: clicked element ID (optional)
    - x, y: click coordinates (optional)
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported",
        )

    # Save uploaded file temporarily
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=".csv",
        delete=False,
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await csv_importer.import_file(tmp_path)
        return result
    finally:
        os.unlink(tmp_path)


@router.post(
    "/single",
    response_model=EventResponse,
    summary="Ingest single event",
    description="Receive and process a single clickstream event.",
)
async def create_single_event(
    event: Event,
    request: Request,
) -> EventResponse:
    """
    Ingest a single clickstream event.

    Convenience endpoint for sending individual events.
    """
    client_ip = request.client.host if request.client else None

    response = await event_processor.process_single_event(
        event,
        source="http",
        client_ip=client_ip,
    )

    record_event_processed("http", event.type.value)

    return response
