"""
Configuration module for Clickstream Analytics.

Uses pydantic-settings for environment variable management.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Clickstream Analytics"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # ClickHouse
    clickhouse_host: str = "clickhouse-1"
    clickhouse_port: int = 9000
    clickhouse_http_port: int = 8123
    clickhouse_user: str = "clickstream"
    clickhouse_password: str = "clickstream123"
    clickhouse_database: str = "clickstream"

    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "clickstream"
    postgres_password: str = "clickstream123"
    postgres_database: str = "clickstream"

    # Kafka
    kafka_bootstrap_servers: str = "kafka-1:29092,kafka-2:29092,kafka-3:29092"
    kafka_topic: str = "clickstream-events"
    kafka_group_id: str = "clickstream-consumer"
    kafka_auto_offset_reset: str = "earliest"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    # Event Processing
    batch_size: int = 1000
    batch_timeout_ms: int = 5000

    @property
    def postgres_dsn(self) -> str:
        """Generate PostgreSQL connection string."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )

    @property
    def postgres_sync_dsn(self) -> str:
        """Generate PostgreSQL sync connection string."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )

    @property
    def clickhouse_dsn(self) -> str:
        """Generate ClickHouse connection string."""
        return (
            f"clickhouse://{self.clickhouse_user}:{self.clickhouse_password}"
            f"@{self.clickhouse_host}:{self.clickhouse_port}/{self.clickhouse_database}"
        )

    @property
    def redis_url(self) -> str:
        """Generate Redis connection URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def kafka_servers_list(self) -> List[str]:
        """Get Kafka bootstrap servers as list."""
        return [s.strip() for s in self.kafka_bootstrap_servers.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
