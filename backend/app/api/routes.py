"""
API router configuration.
"""

from fastapi import APIRouter

from app.api.events import router as events_router
from app.api.stats import router as stats_router
from app.api.health import router as health_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(
    events_router,
    prefix="/events",
    tags=["Events"],
)

api_router.include_router(
    stats_router,
    prefix="/stats",
    tags=["Statistics"],
)

api_router.include_router(
    health_router,
    tags=["Health"],
)
