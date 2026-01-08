# Superset configuration for Clickstream Analytics

import os
from datetime import timedelta

# General
SUPERSET_WEBSERVER_PORT = 8088
SECRET_KEY = os.getenv("SUPERSET_SECRET_KEY", "clickstream_superset_secret_key_123")

# Database
SQLALCHEMY_DATABASE_URI = os.getenv(
    "SQLALCHEMY_DATABASE_URI",
    "postgresql+psycopg2://superset:superset@superset-db:5432/superset"
)

# Cache
CACHE_CONFIG = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 60 * 60 * 24,
}

# Feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
}

# Security
WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = []
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24 * 365

# Authentication
AUTH_TYPE = 1  # AUTH_DB

# Celery (optional, for async queries)
# CELERY_CONFIG = {
#     "broker_url": "redis://redis:6379/1",
#     "result_backend": "redis://redis:6379/1",
# }

# SQL Lab
SQL_MAX_ROW = 100000
SQLLAB_TIMEOUT = 300
SQLLAB_DEFAULT_DBID = 1

# Logging
LOG_FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
LOG_LEVEL = "INFO"

# Additional databases
# ClickHouse connection for analytics
DATABASES = {
    "clickhouse": {
        "allow_ctas": False,
        "allow_cvas": False,
        "allow_dml": False,
        "sqlalchemy_uri": "clickhouse+http://clickstream:clickstream123@clickhouse-1:8123/clickstream",
    }
}
