"""
Prometheus metrics for Clickstream Analytics.
"""

from app.metrics.prometheus import (
    setup_metrics,
    EVENTS_PROCESSED,
    EVENTS_ERRORS,
    HTTP_REQUESTS,
    HTTP_REQUEST_DURATION,
)

__all__ = [
    "setup_metrics",
    "EVENTS_PROCESSED",
    "EVENTS_ERRORS",
    "HTTP_REQUESTS",
    "HTTP_REQUEST_DURATION",
]
