# Superset with ClickHouse driver
FROM apache/superset:3.1.0

USER root

# Install ClickHouse driver and requests for init script
RUN pip install --no-cache-dir clickhouse-connect==0.6.8 requests

# Copy init script
COPY --chown=superset:superset init_superset.py /app/init_superset.py

USER superset
