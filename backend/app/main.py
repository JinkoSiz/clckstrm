"""
Clickstream Analytics - Main Application

FastAPI application for collecting and analyzing clickstream events.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config import settings
from app.metrics.prometheus import setup_metrics
from app.repositories.postgres import postgres_repo
from app.services.kafka_consumer import kafka_consumer

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Clickstream Analytics...")

    # Connect to PostgreSQL
    try:
        await postgres_repo.connect()
        logger.info("PostgreSQL connection established")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")

    # Start Kafka consumer
    try:
        await kafka_consumer.start()
        logger.info("Kafka consumer started")
    except Exception as e:
        logger.warning(f"Failed to start Kafka consumer: {e}")

    logger.info("Clickstream Analytics started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Clickstream Analytics...")

    # Stop Kafka consumer
    try:
        await kafka_consumer.stop()
        logger.info("Kafka consumer stopped")
    except Exception as e:
        logger.error(f"Error stopping Kafka consumer: {e}")

    # Close PostgreSQL connection
    try:
        await postgres_repo.close()
        logger.info("PostgreSQL connection closed")
    except Exception as e:
        logger.error(f"Error closing PostgreSQL connection: {e}")

    logger.info("Clickstream Analytics shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## Clickstream Analytics API

    Система сбора и анализа кликстрим-событий.

    ### Возможности

    * **Сбор событий** - приём событий view/click через HTTP API
    * **Статистика** - аналитические данные для дашбордов
    * **Фильтрация** - поиск событий по различным критериям

    ### Источники данных

    * HTTP API
    * Apache Kafka
    * CSV файлы
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Prometheus metrics
setup_metrics(app)

# Include API routes
app.include_router(api_router)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
        "metrics": "/metrics",
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
