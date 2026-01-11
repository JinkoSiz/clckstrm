# Airflow with ClickHouse driver
FROM apache/airflow:2.8.0-python3.11

USER root

# Install system dependencies for clickhouse-driver
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install ClickHouse driver
RUN pip install --no-cache-dir clickhouse-driver==0.2.6
