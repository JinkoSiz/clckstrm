#!/bin/bash
# Initialize Superset with ClickHouse database and sample charts
# Run this script after Superset is fully started

set -e

echo "=== Initializing Superset ==="

# Wait for Superset to be ready
echo "Waiting for Superset to be ready..."
until curl -s -f http://localhost:8088/health > /dev/null 2>&1; do
    echo "Waiting..."
    sleep 5
done
echo "Superset is ready!"

# Get CSRF token and login
echo "Logging in to Superset..."
CSRF_TOKEN=$(curl -s -c cookies.txt -b cookies.txt http://localhost:8088/login/ | grep -oP 'name="csrf_token"[^>]*value="\K[^"]+' || echo "")

curl -s -X POST http://localhost:8088/login/ \
    -c cookies.txt -b cookies.txt \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin&password=admin&csrf_token=${CSRF_TOKEN}" > /dev/null

# Get API access token
echo "Getting API access token..."
ACCESS_TOKEN=$(curl -s -X POST http://localhost:8088/api/v1/security/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin", "provider": "db", "refresh": true}' | grep -oP '"access_token":"\K[^"]+')

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Failed to get access token. Using session cookies..."
    AUTH_HEADER=""
else
    AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"
fi

# Create ClickHouse database connection
echo "Creating ClickHouse database connection..."
curl -s -X POST http://localhost:8088/api/v1/database/ \
    -H "Content-Type: application/json" \
    -H "$AUTH_HEADER" \
    -b cookies.txt \
    -d '{
        "database_name": "ClickHouse Analytics",
        "sqlalchemy_uri": "clickhousedb://clickstream:clickstream123@clickhouse-1:8123/clickstream",
        "expose_in_sqllab": true,
        "allow_ctas": false,
        "allow_cvas": false,
        "allow_dml": false
    }' || echo "Database may already exist"

echo ""
echo "=== Superset Initialization Complete ==="
echo ""
echo "Access Superset at: http://localhost:8088"
echo "Login: admin / admin"
echo ""
echo "To add datasets manually:"
echo "1. Go to Data -> Datasets -> + Dataset"
echo "2. Select database: ClickHouse Analytics"
echo "3. Select schema: clickstream"
echo "4. Select table: events_processed"
echo ""
echo "Available tables:"
echo "  - events_processed (processed events with parsed data)"
echo "  - events_raw (raw events as received)"

rm -f cookies.txt
