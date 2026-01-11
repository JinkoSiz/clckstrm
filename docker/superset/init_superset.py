#!/usr/bin/env python3
"""
Superset initialization script using REST API.
Creates database connection, datasets, charts, and dashboard.

Run after Superset is up:
  docker exec superset python /app/pythonpath/init_superset.py
"""

import json
import logging
import time
import requests
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPERSET_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"
MAX_RETRIES = 30
RETRY_DELAY = 5


def wait_for_superset():
    """Wait for Superset to be fully ready."""
    logger.info("Waiting for Superset to be ready...")
    for i in range(MAX_RETRIES):
        try:
            # Check health endpoint
            response = requests.get(f"{SUPERSET_URL}/health", timeout=5)
            if response.status_code == 200:
                # Try to login to verify API is ready
                login_response = requests.post(
                    f"{SUPERSET_URL}/api/v1/security/login",
                    json={"username": USERNAME, "password": PASSWORD, "provider": "db", "refresh": True},
                    timeout=10
                )
                if login_response.status_code == 200:
                    logger.info(f"Superset is ready after {i * RETRY_DELAY} seconds")
                    return True
        except requests.exceptions.RequestException:
            pass
        logger.info(f"Waiting for Superset... ({i + 1}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY)
    logger.error("Superset did not become ready in time")
    return False


class SupersetAPI:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token = None
        self.csrf_token = None
        self._login(username, password)

    def _login(self, username, password):
        """Login and get access token."""
        # Get access token
        login_url = urljoin(self.base_url, "/api/v1/security/login")
        response = self.session.post(login_url, json={
            "username": username,
            "password": password,
            "provider": "db",
            "refresh": True
        })

        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            })
            logger.info("Successfully logged in to Superset")
        else:
            raise Exception(f"Login failed: {response.text}")

        # Get CSRF token
        csrf_url = urljoin(self.base_url, "/api/v1/security/csrf_token/")
        response = self.session.get(csrf_url)
        if response.status_code == 200:
            self.csrf_token = response.json().get("result")
            self.session.headers.update({"X-CSRFToken": self.csrf_token})
            logger.info("Got CSRF token")

    def _request(self, method, endpoint, **kwargs):
        """Make API request."""
        url = urljoin(self.base_url, endpoint)
        response = self.session.request(method, url, **kwargs)
        return response

    def create_database(self, name, sqlalchemy_uri):
        """Create database connection."""
        # Check if exists
        response = self._request("GET", "/api/v1/database/")
        if response.status_code == 200:
            for db in response.json().get("result", []):
                if db.get("database_name") == name:
                    logger.info(f"Database '{name}' already exists with id={db['id']}")
                    return db["id"]

        # Create new
        data = {
            "database_name": name,
            "sqlalchemy_uri": sqlalchemy_uri,
            "expose_in_sqllab": True,
            "allow_ctas": False,
            "allow_cvas": False,
            "allow_dml": False,
            "allow_run_async": True,
            "extra": json.dumps({
                "engine_params": {
                    "connect_args": {"connect_timeout": 10}
                }
            })
        }

        response = self._request("POST", "/api/v1/database/", json=data)
        if response.status_code in [200, 201]:
            db_id = response.json().get("id")
            logger.info(f"Created database '{name}' with id={db_id}")
            return db_id
        else:
            logger.error(f"Failed to create database: {response.text}")
            return None

    def create_dataset(self, database_id, table_name, schema="clickstream"):
        """Create dataset from table."""
        # Check if exists
        response = self._request("GET", "/api/v1/dataset/")
        if response.status_code == 200:
            for ds in response.json().get("result", []):
                if ds.get("table_name") == table_name:
                    logger.info(f"Dataset '{table_name}' already exists with id={ds['id']}")
                    return ds["id"]

        # Create new
        data = {
            "database": database_id,
            "table_name": table_name,
            "schema": schema
        }

        response = self._request("POST", "/api/v1/dataset/", json=data)
        if response.status_code in [200, 201]:
            ds_id = response.json().get("id")
            logger.info(f"Created dataset '{table_name}' with id={ds_id}")
            return ds_id
        else:
            logger.error(f"Failed to create dataset '{table_name}': {response.text}")
            return None

    def create_chart(self, name, viz_type, datasource_id, params, datasource_type="table"):
        """Create chart."""
        # Check if exists
        response = self._request("GET", "/api/v1/chart/")
        if response.status_code == 200:
            for chart in response.json().get("result", []):
                if chart.get("slice_name") == name:
                    logger.info(f"Chart '{name}' already exists with id={chart['id']}")
                    return chart["id"]

        # Create new
        data = {
            "slice_name": name,
            "viz_type": viz_type,
            "datasource_id": datasource_id,
            "datasource_type": datasource_type,
            "params": json.dumps(params)
        }

        response = self._request("POST", "/api/v1/chart/", json=data)
        if response.status_code in [200, 201]:
            chart_id = response.json().get("id")
            logger.info(f"Created chart '{name}' with id={chart_id}")
            return chart_id
        else:
            logger.error(f"Failed to create chart '{name}': {response.text}")
            return None

    def delete_dashboard(self, slug):
        """Delete dashboard by slug."""
        response = self._request("GET", "/api/v1/dashboard/")
        if response.status_code == 200:
            for dash in response.json().get("result", []):
                if dash.get("slug") == slug:
                    self._request("DELETE", f"/api/v1/dashboard/{dash['id']}")
                    logger.info(f"Deleted dashboard with slug '{slug}'")
                    return True
        return False

    def create_dashboard(self, title, slug, chart_ids, force_recreate=False):
        """Create dashboard with charts."""
        # Check if exists
        response = self._request("GET", "/api/v1/dashboard/")
        if response.status_code == 200:
            for dash in response.json().get("result", []):
                if dash.get("slug") == slug:
                    if force_recreate:
                        self.delete_dashboard(slug)
                        break
                    else:
                        logger.info(f"Dashboard '{title}' already exists with id={dash['id']}")
                        return dash["id"]

        # Build position_json with grid layout for charts
        position_json = {
            "DASHBOARD_VERSION_KEY": "v2",
            "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
            "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
            "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": title}}
        }

        # Add each chart to the grid (2 columns layout)
        row_id = 0
        for i, chart_id in enumerate(chart_ids):
            row_key = f"ROW-{row_id}"
            chart_key = f"CHART-{chart_id}"

            # Create row if needed (every 2 charts)
            if i % 2 == 0:
                position_json[row_key] = {
                    "type": "ROW",
                    "id": row_key,
                    "children": [],
                    "parents": ["ROOT_ID", "GRID_ID"],
                    "meta": {"background": "BACKGROUND_TRANSPARENT"}
                }
                position_json["GRID_ID"]["children"].append(row_key)

            # Add chart to current row
            position_json[chart_key] = {
                "type": "CHART",
                "id": chart_key,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", row_key],
                "meta": {
                    "width": 6,
                    "height": 50,
                    "chartId": chart_id,
                    "sliceName": f"Chart {chart_id}"
                }
            }
            position_json[row_key]["children"].append(chart_key)

            # Move to next row after 2 charts
            if i % 2 == 1:
                row_id += 1

        # Handle odd number of charts
        if len(chart_ids) % 2 == 1:
            row_id += 1

        # Create dashboard with position_json
        data = {
            "dashboard_title": title,
            "slug": slug,
            "published": True,
            "position_json": json.dumps(position_json),
            "json_metadata": json.dumps({
                "timed_refresh_immune_slices": [],
                "expanded_slices": {},
                "refresh_frequency": 0,
                "default_filters": "{}",
                "color_scheme": "supersetColors"
            })
        }

        response = self._request("POST", "/api/v1/dashboard/", json=data)
        if response.status_code not in [200, 201]:
            logger.error(f"Failed to create dashboard: {response.text}")
            return None

        dash_id = response.json().get("id")
        logger.info(f"Created dashboard '{title}' with id={dash_id}")

        # Add slices to dashboard via SQL (Superset API doesn't have direct endpoint)
        import subprocess
        for chart_id in chart_ids:
            try:
                cmd = f"PGPASSWORD=superset psql -h superset-db -U superset -d superset -c \"INSERT INTO dashboard_slices (dashboard_id, slice_id) VALUES ({dash_id}, {chart_id}) ON CONFLICT DO NOTHING;\""
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Added chart {chart_id} to dashboard")
                else:
                    logger.warning(f"Could not add chart {chart_id}: {result.stderr}")
            except Exception as e:
                logger.warning(f"Failed to add chart {chart_id}: {e}")

        logger.info(f"Created dashboard '{title}' with {len(chart_ids)} charts")
        return dash_id


def main():
    """Main initialization function."""
    logger.info("=" * 60)
    logger.info("Starting Superset initialization...")
    logger.info("=" * 60)

    # Wait for Superset to be fully ready
    if not wait_for_superset():
        logger.error("Superset is not ready. Exiting.")
        return

    api = SupersetAPI(SUPERSET_URL, USERNAME, PASSWORD)

    # 1. Create ClickHouse database connection
    logger.info("\n>>> Creating ClickHouse database connection...")
    db_id = api.create_database(
        name="ClickHouse Analytics",
        sqlalchemy_uri="clickhousedb://clickstream:clickstream123@clickhouse-1:8123/clickstream"
    )

    if not db_id:
        logger.error("Failed to create database. Exiting.")
        return

    # Wait for database to be ready
    time.sleep(2)

    # 2. Create datasets
    logger.info("\n>>> Creating datasets...")
    events_processed_id = api.create_dataset(db_id, "events_processed")
    events_raw_id = api.create_dataset(db_id, "events_raw")

    if not events_processed_id:
        logger.error("Failed to create events_processed dataset. Exiting.")
        return

    # Wait for datasets to be ready
    time.sleep(2)

    # 3. Create charts
    logger.info("\n>>> Creating charts...")
    chart_ids = []

    # Chart 1: Events by Type (Pie)
    chart_id = api.create_chart(
        name="Events by Type",
        viz_type="pie",
        datasource_id=events_processed_id,
        params={
            "metric": "count",
            "groupby": ["event_type"],
            "row_limit": 100,
            "color_scheme": "supersetColors",
            "show_legend": True,
            "show_labels": True,
            "label_type": "key_value",
            "number_format": "SMART_NUMBER"
        }
    )
    if chart_id:
        chart_ids.append(chart_id)

    # Chart 2: Events by Device Type (Pie)
    chart_id = api.create_chart(
        name="Events by Device",
        viz_type="pie",
        datasource_id=events_processed_id,
        params={
            "metric": "count",
            "groupby": ["device_type"],
            "row_limit": 100,
            "color_scheme": "supersetColors",
            "show_legend": True
        }
    )
    if chart_id:
        chart_ids.append(chart_id)

    # Chart 3: Events by Browser (Bar)
    chart_id = api.create_chart(
        name="Events by Browser",
        viz_type="dist_bar",
        datasource_id=events_processed_id,
        params={
            "metrics": ["count"],
            "groupby": ["browser"],
            "row_limit": 10,
            "color_scheme": "supersetColors",
            "show_legend": False,
            "y_axis_format": "SMART_NUMBER",
            "order_desc": True
        }
    )
    if chart_id:
        chart_ids.append(chart_id)

    # Chart 4: Events by OS (Bar)
    chart_id = api.create_chart(
        name="Events by OS",
        viz_type="dist_bar",
        datasource_id=events_processed_id,
        params={
            "metrics": ["count"],
            "groupby": ["os"],
            "row_limit": 10,
            "color_scheme": "supersetColors",
            "show_legend": False,
            "order_desc": True
        }
    )
    if chart_id:
        chart_ids.append(chart_id)

    # Chart 5: Top Pages (Table)
    chart_id = api.create_chart(
        name="Top Pages",
        viz_type="table",
        datasource_id=events_processed_id,
        params={
            "metrics": ["count"],
            "groupby": ["url_path"],
            "row_limit": 20,
            "order_desc": True,
            "table_timestamp_format": "smart_date",
            "page_length": 20
        }
    )
    if chart_id:
        chart_ids.append(chart_id)

    # Chart 6: Events by Country (Pie)
    chart_id = api.create_chart(
        name="Events by Country",
        viz_type="pie",
        datasource_id=events_processed_id,
        params={
            "metric": "count",
            "groupby": ["country"],
            "row_limit": 20,
            "color_scheme": "supersetColors",
            "show_legend": True
        }
    )
    if chart_id:
        chart_ids.append(chart_id)

    # 4. Create dashboard (force recreate to fix layout)
    if chart_ids:
        logger.info("\n>>> Creating dashboard...")
        api.create_dashboard(
            title="Clickstream Analytics",
            slug="clickstream-analytics",
            chart_ids=chart_ids,
            force_recreate=True
        )

    logger.info("\n" + "=" * 60)
    logger.info("Superset initialization complete!")
    logger.info("=" * 60)
    logger.info(f"\nAccess Superset at: {SUPERSET_URL}")
    logger.info("Login: admin / admin")
    logger.info("\nCreated:")
    logger.info(f"  - Database: ClickHouse Analytics")
    logger.info(f"  - Datasets: events_processed, events_raw")
    logger.info(f"  - Charts: {len(chart_ids)} charts")
    logger.info(f"  - Dashboard: Clickstream Analytics")


if __name__ == "__main__":
    main()
