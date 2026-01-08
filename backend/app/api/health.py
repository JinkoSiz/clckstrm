"""
Health check endpoints.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.repositories.clickhouse import clickhouse_repo
from app.repositories.postgres import postgres_repo
from app.services.kafka_consumer import kafka_consumer

router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    description="Check application health status.",
)
async def health_check() -> dict:
    """
    Basic health check endpoint.
    Returns simple OK status if application is running.
    """
    return {"status": "ok"}


@router.get(
    "/health/detailed",
    summary="Detailed health check",
    description="Check health of all system components.",
)
async def detailed_health_check() -> JSONResponse:
    """
    Detailed health check for all components.
    Checks:
    - ClickHouse connection
    - PostgreSQL connection
    - Kafka consumer status
    """
    components = {}
    all_healthy = True

    # Check ClickHouse
    try:
        ch_healthy = clickhouse_repo.health_check()
        components["clickhouse"] = {
            "status": "healthy" if ch_healthy else "unhealthy",
            "message": "Connected" if ch_healthy else "Connection failed",
        }
        if not ch_healthy:
            all_healthy = False
    except Exception as e:
        components["clickhouse"] = {
            "status": "unhealthy",
            "message": str(e),
        }
        all_healthy = False

    # Check PostgreSQL
    try:
        pg_healthy = await postgres_repo.health_check()
        components["postgres"] = {
            "status": "healthy" if pg_healthy else "unhealthy",
            "message": "Connected" if pg_healthy else "Connection failed",
        }
        if not pg_healthy:
            all_healthy = False
    except Exception as e:
        components["postgres"] = {
            "status": "unhealthy",
            "message": str(e),
        }
        all_healthy = False

    # Check Kafka consumer
    try:
        kafka_running = kafka_consumer.is_running
        components["kafka_consumer"] = {
            "status": "healthy" if kafka_running else "stopped",
            "message": "Running" if kafka_running else "Not running",
        }
    except Exception as e:
        components["kafka_consumer"] = {
            "status": "unknown",
            "message": str(e),
        }

    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "components": components,
        },
    )


@router.get(
    "/ready",
    summary="Readiness check",
    description="Check if application is ready to serve requests.",
)
async def readiness_check() -> JSONResponse:
    """
    Returns 200 if all critical components are ready.
    """
    try:
        # Check critical components
        ch_ready = clickhouse_repo.health_check()
        pg_ready = await postgres_repo.health_check()

        if ch_ready and pg_ready:
            return JSONResponse(
                status_code=200,
                content={"status": "ready"},
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "clickhouse": ch_ready,
                    "postgres": pg_ready,
                },
            )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)},
        )


@router.get(
    "/live",
    summary="Liveness check",
    description="Check if application is alive.",
)
async def liveness_check() -> dict:
    """
    Returns 200 if application process is running.
    """
    return {"status": "alive"}
