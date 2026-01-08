# Superset with ClickHouse driver
FROM apache/superset:3.1.0

USER root

# Install ClickHouse driver (clickhouse-connect is SQLAlchemy 1.x compatible)
RUN pip install --no-cache-dir clickhouse-connect==0.6.8

USER superset
