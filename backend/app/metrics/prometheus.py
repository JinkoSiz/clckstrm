"""
Prometheus metrics configuration.
"""

from prometheus_client import Counter, Histogram, Info
from prometheus_fastapi_instrumentator import Instrumentator

# Application info
APP_INFO = Info("clickstream_app", "Clickstream Analytics application info")

# Event processing metrics
EVENTS_PROCESSED = Counter(
    "clickstream_events_processed_total",
    "Total number of processed events",
    ["source", "event_type"],
)

EVENTS_ERRORS = Counter(
    "clickstream_events_errors_total",
    "Total number of event processing errors",
    ["source", "error_type"],
)

# HTTP metrics (additional custom metrics)
HTTP_REQUESTS = Counter(
    "clickstream_http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "clickstream_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Kafka metrics
KAFKA_MESSAGES_CONSUMED = Counter(
    "clickstream_kafka_messages_consumed_total",
    "Total number of Kafka messages consumed",
    ["topic"],
)

KAFKA_CONSUMER_LAG = Histogram(
    "clickstream_kafka_consumer_lag",
    "Kafka consumer lag in messages",
    ["topic", "partition"],
)

# Database metrics
DB_QUERY_DURATION = Histogram(
    "clickstream_db_query_duration_seconds",
    "Database query duration in seconds",
    ["database", "operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

DB_CONNECTIONS_ACTIVE = Counter(
    "clickstream_db_connections_active",
    "Number of active database connections",
    ["database"],
)


def setup_metrics(app):
    """
    Setup Prometheus metrics for FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Set application info
    APP_INFO.info({
        "version": "1.0.0",
        "name": "Clickstream Analytics",
    })

    # Setup FastAPI instrumentator
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health", "/api/v1/health"],
        inprogress_name="clickstream_http_requests_inprogress",
        inprogress_labels=True,
    )

    # Instrument application
    instrumentator.instrument(app)

    # Expose metrics endpoint
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=True)

    return instrumentator


def record_event_processed(source: str, event_type: str, count: int = 1):
    """Record processed events metric."""
    EVENTS_PROCESSED.labels(source=source, event_type=event_type).inc(count)


def record_event_error(source: str, error_type: str):
    """Record event processing error metric."""
    EVENTS_ERRORS.labels(source=source, error_type=error_type).inc()


def record_http_request(method: str, endpoint: str, status: int):
    """Record HTTP request metric."""
    HTTP_REQUESTS.labels(
        method=method, endpoint=endpoint, status=str(status)
    ).inc()


def record_http_duration(method: str, endpoint: str, duration: float):
    """Record HTTP request duration metric."""
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)


def record_db_query_duration(database: str, operation: str, duration: float):
    """Record database query duration metric."""
    DB_QUERY_DURATION.labels(database=database, operation=operation).observe(duration)
