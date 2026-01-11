"""
ClickHouse Airflow Plugin

Custom operators and hooks for ClickHouse integration.
"""

import os
from typing import Any, Dict, List, Optional

from airflow.hooks.base import BaseHook
from airflow.models import BaseOperator


class ClickHouseHook(BaseHook):
    """
    Hook for interacting with ClickHouse.
    """

    conn_name_attr = "clickhouse_conn_id"
    default_conn_name = "clickhouse_default"
    conn_type = "clickhouse"
    hook_name = "ClickHouse"

    def __init__(
        self,
        clickhouse_conn_id: str = default_conn_name,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        super().__init__()
        self.clickhouse_conn_id = clickhouse_conn_id
        self.host = host or os.getenv("CLICKHOUSE_HOST", "clickhouse-1")
        self.port = port or int(os.getenv("CLICKHOUSE_PORT", "9000"))
        self.user = user or os.getenv("CLICKHOUSE_USER", "clickstream")
        self.password = password or os.getenv("CLICKHOUSE_PASSWORD", "clickstream123")
        self.database = database or os.getenv("CLICKHOUSE_DATABASE", "clickstream")
        self._client = None

    def get_conn(self):
        """Get ClickHouse connection."""
        if self._client is None:
            from clickhouse_driver import Client

            self._client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
            )
        return self._client

    def execute(self, query: str, params: Optional[Dict] = None) -> List:
        """Execute query and return results."""
        client = self.get_conn()
        return client.execute(query, params or {})

    def execute_many(self, query: str, data: List[Dict]) -> None:
        """Execute query with multiple data rows."""
        client = self.get_conn()
        client.execute(query, data)

    def close(self) -> None:
        """Close connection."""
        if self._client:
            self._client.disconnect()
            self._client = None


class ClickHouseOperator(BaseOperator):
    """
    Operator for executing ClickHouse queries.

    :param sql: SQL query to execute
    :param clickhouse_conn_id: ClickHouse connection ID
    :param parameters: Query parameters
    """

    template_fields = ("sql", "parameters")
    template_ext = (".sql",)
    ui_color = "#ffcc00"

    def __init__(
        self,
        sql: str,
        clickhouse_conn_id: str = "clickhouse_default",
        parameters: Optional[Dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.sql = sql
        self.clickhouse_conn_id = clickhouse_conn_id
        self.parameters = parameters or {}

    def execute(self, context: Dict) -> Any:
        """Execute the operator."""
        self.log.info(f"Executing ClickHouse query: {self.sql[:100]}...")

        hook = ClickHouseHook()

        try:
            result = hook.execute(self.sql, self.parameters)
            self.log.info(f"Query executed successfully, rows affected: {len(result) if result else 0}")
            return result
        finally:
            hook.close()


class ClickHouseInsertOperator(BaseOperator):
    """
    Operator for bulk inserting data into ClickHouse.

    :param table: Target table name
    :param data: List of dictionaries to insert
    :param clickhouse_conn_id: ClickHouse connection ID
    """

    template_fields = ("table",)
    ui_color = "#ffcc00"

    def __init__(
        self,
        table: str,
        data: List[Dict],
        clickhouse_conn_id: str = "clickhouse_default",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.table = table
        self.data = data
        self.clickhouse_conn_id = clickhouse_conn_id

    def execute(self, context: Dict) -> int:
        """Execute the operator."""
        if not self.data:
            self.log.info("No data to insert")
            return 0

        self.log.info(f"Inserting {len(self.data)} rows into {self.table}")

        hook = ClickHouseHook()

        try:
            # Get column names from first row
            columns = list(self.data[0].keys())
            columns_str = ", ".join(columns)

            query = f"INSERT INTO {self.table} ({columns_str}) VALUES"
            hook.execute_many(query, self.data)

            self.log.info(f"Successfully inserted {len(self.data)} rows")
            return len(self.data)
        finally:
            hook.close()
