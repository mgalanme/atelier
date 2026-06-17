"""
Bronze ingestion: lands raw source data into the atelier.bronze schema.

Sources landed here are intentionally left close to their original shape.
No business logic, validation or deduplication happens at this stage; that
is deferred to the Silver notebook, so that a change in business rules never
requires re-pulling from the source system.
"""

import os
import uuid

from databricks import sql
from dotenv import load_dotenv

load_dotenv()

CATALOG = os.environ["ATELIER_CATALOG"]
BRONZE_SCHEMA = os.environ["ATELIER_SCHEMA_BRONZE"]

BRONZE_TABLES = {
    "trend_signals_raw": ["signal_id", "source", "season", "colour", "silhouette", "captured_at", "payload"],
    "inventory_raw": ["sku", "warehouse", "quantity_on_hand", "as_of_date", "payload"],
    "sales_history_raw": ["order_id", "sku", "market", "units_sold", "sale_date", "payload"],
    "climate_raw": ["region", "season", "avg_temp_c", "avg_rainfall_mm", "captured_at"],
    "social_listening_raw": ["post_id", "platform", "captured_at", "sentiment_score", "payload"],
}


def get_connection():
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"].replace("https://", ""),
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def ensure_bronze_tables(cursor):
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{BRONZE_SCHEMA}")
    for table_name, columns in BRONZE_TABLES.items():
        column_defs = ", ".join(f"{c} STRING" for c in columns)
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {CATALOG}.{BRONZE_SCHEMA}.{table_name} "
            f"({column_defs}, ingestion_run_id STRING, ingested_at TIMESTAMP)"
        )


def ingest_batch(cursor, table_name, rows: list[dict]):
    """
    Append-only ingestion. A fresh UUID4 run id tags every batch so that a
    failed or partial run can be identified and purged without touching
    rows from any other run.
    """
    run_id = str(uuid.uuid4())
    columns = BRONZE_TABLES[table_name]
    for row in rows:
        values = ", ".join(f"'{str(row.get(c, '')).replace(chr(39), chr(39) * 2)}'" for c in columns)
        cursor.execute(
            f"INSERT INTO {CATALOG}.{BRONZE_SCHEMA}.{table_name} "
            f"({', '.join(columns)}, ingestion_run_id, ingested_at) "
            f"VALUES ({values}, '{run_id}', current_timestamp())"
        )
    return run_id


if __name__ == "__main__":
    connection = get_connection()
    with connection.cursor() as cursor:
        ensure_bronze_tables(cursor)
        # Replace the empty lists below with the actual extract calls
        # against each source connector (trend provider, climate API,
        # social listening API, internal inventory and sales exports).
        ingest_batch(cursor, "trend_signals_raw", [])
        ingest_batch(cursor, "inventory_raw", [])
        ingest_batch(cursor, "sales_history_raw", [])
        ingest_batch(cursor, "climate_raw", [])
        ingest_batch(cursor, "social_listening_raw", [])
    connection.close()
